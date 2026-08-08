"""
Stage 04 - Export a Power BI ready star schema.

Kimball dimensional model. Facts hold measures and foreign keys only; all
descriptive attributes live in dimensions. dim_payer is a Type 2 slowly
changing dimension because issuer names change across plan years while the
issuer ID persists, and denial history must stay attached to the name in force
at the time.

Outputs (data/processed/star/)
    dim_date.csv            experience year grain
    dim_payer.csv           SCD Type 2 on issuer name
    dim_plan.csv            plan attributes
    dim_geography.csv       state
    dim_denial_reason.csv   reason with RCM root cause, owner, CARC examples
    fact_claims_summary.csv issuer-year claim and appeal measures
    fact_denials.csv        plan-year denials by reason
    measures.dax            DAX measure definitions for the Power BI model
"""
import numpy as np
import pandas as pd

from config import DENIAL_REASON_COLS, PROCESSED, ROOT_CAUSE_TAXONOMY

STAR = PROCESSED / "star"
STAR.mkdir(parents=True, exist_ok=True)


def build_dim_date(plan):
    yrs = sorted(plan["experience_year"].dropna().unique())
    return pd.DataFrame({
        "date_key": [int(y) for y in yrs],
        "experience_year": [int(y) for y in yrs],
        "plan_year_file": [int(y) + 2 for y in yrs],
        "is_latest": [y == max(yrs) for y in yrs],
    })


def build_dim_payer(iss):
    """
    Type 2 SCD. A new row is issued whenever an issuer's reported name changes,
    so a denial recorded in 2021 stays attached to the name used in 2021.
    """
    d = (iss[["issuer_id", "issuer_name", "state", "experience_year"]]
         .dropna(subset=["issuer_id"]).sort_values(["issuer_id", "experience_year"]))
    d["issuer_name"] = d["issuer_name"].astype(str).str.strip()

    rows, key = [], 1
    for iid, g in d.groupby("issuer_id"):
        g = g.sort_values("experience_year")
        cur_name, start = None, None
        prev_year = None
        for _, r in g.iterrows():
            if cur_name is None:
                cur_name, start = r["issuer_name"], int(r["experience_year"])
            elif r["issuer_name"] != cur_name:
                rows.append(dict(payer_key=key, issuer_id=int(iid), issuer_name=cur_name,
                                 state=r["state"], valid_from_year=start,
                                 valid_to_year=int(prev_year), is_current=False))
                key += 1
                cur_name, start = r["issuer_name"], int(r["experience_year"])
            prev_year = int(r["experience_year"])
        rows.append(dict(payer_key=key, issuer_id=int(iid), issuer_name=cur_name,
                         state=g.iloc[-1]["state"], valid_from_year=start,
                         valid_to_year=9999, is_current=True))
        key += 1
    return pd.DataFrame(rows)


def build_dim_plan(plan):
    d = (plan[["plan_id", "issuer_id", "plan_type", "metal_level", "product_type", "state"]]
         .dropna(subset=["plan_id"]).drop_duplicates(subset=["plan_id"]).copy())
    d.insert(0, "plan_key", range(1, len(d) + 1))
    d["metal_level"] = d["metal_level"].replace({"Nan": "Unknown", "": "Unknown"}).fillna("Unknown")
    d["plan_type"] = d["plan_type"].replace({"NAN": "Unknown", "": "Unknown"}).fillna("Unknown")
    return d


def build_dim_geography(plan):
    st = sorted(plan["state"].dropna().unique())
    return pd.DataFrame({"geo_key": range(1, len(st) + 1), "state": st})


def build_dim_denial_reason():
    rows = []
    for i, (col, meta) in enumerate(ROOT_CAUSE_TAXONOMY.items(), start=1):
        rows.append(dict(
            reason_key=i, denial_reason_code=col,
            denial_reason_label=col.replace("den_", "").replace("_", " ").title(),
            rcm_root_cause=meta["root_cause"], accountable_owner=meta["owner"],
            x12_carc_examples=meta["x12_carc_examples"],
            preventability=meta["preventability"], appealability=meta["appealability"],
            effort_hours_per_appeal=meta["effort_hours"],
            rcm_stage=meta["root_cause"].split(":")[0].strip()))
    return pd.DataFrame(rows)


def build_fact_claims(iss, dim_payer, dim_geo):
    f = iss.copy()
    pk = dim_payer[dim_payer.is_current][["issuer_id", "payer_key"]]
    f = f.merge(pk, on="issuer_id", how="left")
    f = f.merge(dim_geo, on="state", how="left")
    f["date_key"] = f["experience_year"].astype("Int64")
    cols = ["date_key", "payer_key", "geo_key", "plan_count",
            "issuer_claims_received_total", "issuer_claims_received_in",
            "issuer_claims_received_out", "issuer_claims_denied_total",
            "issuer_claims_denied_in", "issuer_claims_denied_out",
            "issuer_claims_resubmitted_total", "issuer_internal_appeals_filed",
            "issuer_internal_appeals_overturned", "issuer_external_appeals_filed",
            "issuer_external_appeals_overturned"]
    f = f[[c for c in cols if c in f.columns]].copy()
    return f.rename(columns={
        "issuer_claims_received_total": "claims_received",
        "issuer_claims_received_in": "claims_received_in_network",
        "issuer_claims_received_out": "claims_received_out_of_network",
        "issuer_claims_denied_total": "claims_denied",
        "issuer_claims_denied_in": "claims_denied_in_network",
        "issuer_claims_denied_out": "claims_denied_out_of_network",
        "issuer_claims_resubmitted_total": "claims_resubmitted",
        "issuer_internal_appeals_filed": "internal_appeals_filed",
        "issuer_internal_appeals_overturned": "internal_appeals_overturned",
        "issuer_external_appeals_filed": "external_appeals_filed",
        "issuer_external_appeals_overturned": "external_appeals_overturned"})


def build_fact_denials(plan, dim_plan, dim_reason, dim_geo):
    """Unpivot the ten reason columns to one row per plan-year per reason."""
    keep = ["plan_id", "experience_year", "state", "reason_reconciles"] + DENIAL_REASON_COLS
    d = plan[keep].copy()
    long = d.melt(id_vars=["plan_id", "experience_year", "state", "reason_reconciles"],
                  value_vars=DENIAL_REASON_COLS,
                  var_name="denial_reason_code", value_name="denials")
    long = long[long["denials"].notna() & (long["denials"] > 0)]
    long = long.merge(dim_plan[["plan_id", "plan_key"]], on="plan_id", how="left")
    long = long.merge(dim_reason[["denial_reason_code", "reason_key"]],
                      on="denial_reason_code", how="left")
    long = long.merge(dim_geo, on="state", how="left")
    long["date_key"] = long["experience_year"].astype("Int64")
    return long[["date_key", "plan_key", "reason_key", "geo_key", "denials",
                 "reason_reconciles"]]


DAX = """// Power BI measures for the RCM Denial Analytics model.
// Paste into a new table named "_Measures" after loading the star schema CSVs.
//
// Relationships to create (all single-direction, many-to-one from fact to dim):
//   fact_claims_summary[date_key]  -> dim_date[date_key]
//   fact_claims_summary[payer_key] -> dim_payer[payer_key]
//   fact_claims_summary[geo_key]   -> dim_geography[geo_key]
//   fact_denials[date_key]         -> dim_date[date_key]
//   fact_denials[plan_key]         -> dim_plan[plan_key]
//   fact_denials[reason_key]       -> dim_denial_reason[reason_key]
//   fact_denials[geo_key]          -> dim_geography[geo_key]

Claims Received = SUM(fact_claims_summary[claims_received])
Claims Denied = SUM(fact_claims_summary[claims_denied])
Claims Resubmitted = SUM(fact_claims_summary[claims_resubmitted])
Appeals Filed = SUM(fact_claims_summary[internal_appeals_filed])
Appeals Overturned = SUM(fact_claims_summary[internal_appeals_overturned])

Denial Rate = DIVIDE([Claims Denied], [Claims Received])
Resubmission Rate = DIVIDE([Claims Resubmitted], [Claims Denied])
Appeal Rate = DIVIDE([Appeals Filed], [Claims Denied])
Overturn Rate = DIVIDE([Appeals Overturned], [Appeals Filed])

Denials Never Appealed = [Claims Denied] - [Appeals Filed]
Share Never Appealed = DIVIDE([Denials Never Appealed], [Claims Denied])

// Peer benchmark: denial rate of the median payer in the current filter context.
Median Payer Denial Rate =
MEDIANX(
    VALUES(dim_payer[payer_key]),
    CALCULATE(DIVIDE([Claims Denied], [Claims Received]))
)

Excess Denial Rate vs Peer = [Denial Rate] - [Median Payer Denial Rate]

// Denials attributable to denying above the peer median.
Excess Denials = [Excess Denial Rate vs Peer] * [Claims Received]

Denials by Reason = SUM(fact_denials[denials])

Reason Share =
DIVIDE(
    [Denials by Reason],
    CALCULATE([Denials by Reason], REMOVEFILTERS(dim_denial_reason))
)

// Reason mix is only meaningful where categories reconcile to reported totals.
Denials by Reason (Reconciling Only) =
CALCULATE([Denials by Reason], fact_denials[reason_reconciles] = TRUE())

Preventable Denials =
SUMX(
    dim_denial_reason,
    [Denials by Reason] * dim_denial_reason[preventability]
)

Appeal Effort Hours =
SUMX(
    dim_denial_reason,
    [Denials by Reason] * dim_denial_reason[appealability]
        * dim_denial_reason[effort_hours_per_appeal]
)

Denial Rate YoY =
VAR Prior = CALCULATE([Denial Rate], dim_date[experience_year] = MAX(dim_date[experience_year]) - 1)
RETURN [Denial Rate] - Prior
"""


def main():
    plan = pd.read_parquet(PROCESSED / "plan_panel.parquet")
    iss = pd.read_parquet(PROCESSED / "issuer_panel.parquet")

    dim_date = build_dim_date(plan)
    dim_payer = build_dim_payer(iss)
    dim_plan = build_dim_plan(plan)
    dim_geo = build_dim_geography(plan)
    dim_reason = build_dim_denial_reason()
    fact_claims = build_fact_claims(iss, dim_payer, dim_geo)
    fact_denials = build_fact_denials(plan, dim_plan, dim_reason, dim_geo)

    tables = {"dim_date": dim_date, "dim_payer": dim_payer, "dim_plan": dim_plan,
              "dim_geography": dim_geo, "dim_denial_reason": dim_reason,
              "fact_claims_summary": fact_claims, "fact_denials": fact_denials}
    for name, t in tables.items():
        t.to_csv(STAR / f"{name}.csv", index=False)

    (STAR / "measures.dax").write_text(DAX, encoding="utf-8")

    # Referential integrity: every fact foreign key must resolve to a dimension.
    problems = []
    for fk, dim, key in [("payer_key", dim_payer, "payer_key"),
                         ("geo_key", dim_geo, "geo_key"),
                         ("date_key", dim_date, "date_key")]:
        if fk in fact_claims.columns:
            orphan = int((~fact_claims[fk].isin(dim[key])).sum())
            if orphan:
                problems.append(f"fact_claims_summary.{fk}: {orphan} orphan rows")
    for fk, dim, key in [("plan_key", dim_plan, "plan_key"),
                         ("reason_key", dim_reason, "reason_key"),
                         ("geo_key", dim_geo, "geo_key")]:
        orphan = int((~fact_denials[fk].isin(dim[key])).sum())
        if orphan:
            problems.append(f"fact_denials.{fk}: {orphan} orphan rows")

    for name, t in tables.items():
        print(f"  {name:22s} {len(t):>8,} rows  {len(t.columns):>2} cols")
    n_scd = len(dim_payer) - dim_payer["issuer_id"].nunique()
    print(f"\ndim_payer SCD2: {dim_payer['issuer_id'].nunique():,} issuers -> "
          f"{len(dim_payer):,} rows ({n_scd} name changes tracked)")
    print(f"referential integrity: {'PASS' if not problems else 'FAIL - ' + '; '.join(problems)}")


if __name__ == "__main__":
    main()
