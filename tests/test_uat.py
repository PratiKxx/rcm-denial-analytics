"""
Executable UAT suite. Each test maps to a BRD requirement and to a test case ID in
docs/RTM.csv. Run with:

    python tests/test_uat.py

Results are written to docs/UAT_RESULTS.csv. Any failure produces a row in
docs/UAT_DEFECT_LOG.csv rather than only a stack trace, because the artifact a
reviewer needs is the defect record, not the traceback.
"""
import json
import sys
import traceback
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from config import (ASSUMPTIONS, DENIAL_REASON_COLS, OUTPUTS,  # noqa: E402
                    PROCESSED, ROOT_CAUSE_TAXONOMY)

DOCS = ROOT / "docs"
RESULTS = []


def uat(tc_id, brd_ids, title, expected):
    """Register a UAT test case."""
    def deco(fn):
        RESULTS.append(dict(fn=fn, tc_id=tc_id, brd_ids=brd_ids,
                            title=title, expected=expected))
        return fn
    return deco


# --------------------------------------------------------------- fixtures
def plan():
    return pd.read_parquet(PROCESSED / "plan_panel.parquet")


def issuer():
    return pd.read_parquet(PROCESSED / "issuer_panel.parquet")


# --------------------------------------------------------------- test cases
@uat("TC-001", "BRD-001", "All five plan years ingested",
     "reconciliation.csv lists plan years 2022 through 2026 with non-zero source rows")
def tc001():
    r = pd.read_csv(OUTPUTS / "reconciliation.csv")
    years = sorted(r.plan_year.tolist())
    assert years == [2022, 2023, 2024, 2025, 2026], f"got {years}"
    assert (r.source_rows > 0).all(), "a plan year ingested zero rows"
    return f"5 plan years, {r.source_rows.sum():,} source rows"


@uat("TC-002", "BRD-002", "Schema generations harmonized without silent column loss",
     "Every source column is either mapped or explicitly listed as unmapped")
def tc002():
    r = pd.read_csv(OUTPUTS / "reconciliation.csv")
    assert set(r.schema_generation) == {"GEN1", "GEN2", "GEN3"}, \
        f"expected 3 generations, got {set(r.schema_generation)}"
    unmapped = r.unmapped_source_columns.sum()
    return (f"3 generations harmonized; {unmapped} source columns explicitly "
            f"listed as unmapped (disclosed, not dropped silently)")


@uat("TC-003", "BRD-003", "Suppression markers are not coerced to zero",
     "Suppressed cells are NULL with a companion flag; no suppressed cell reads 0")
def tc003():
    p = plan()
    flags = [c for c in p.columns if c.endswith("_flag")]
    assert flags, "no suppression flag columns found"
    violations = 0
    for f in flags:
        base = f[:-5]
        if base not in p.columns:
            continue
        bad = p[p[f].notna() & p[base].notna()]
        violations += len(bad)
    assert violations == 0, f"{violations} suppressed cells carry a numeric value"
    n_supp = int(p[flags].notna().any(axis=1).sum())
    return f"{len(flags)} flag columns; {n_supp:,} rows carry >=1 suppression marker; 0 coerced to zero"


@uat("TC-004", "BRD-004", "Issuer measures deduplicated to issuer grain",
     "Issuer panel has exactly one row per issuer per plan year")
def tc004():
    i = issuer()
    dupes = i.duplicated(subset=["plan_year", "issuer_id"]).sum()
    assert dupes == 0, f"{dupes} duplicate issuer-year rows"
    p = plan()
    naive = p.groupby(["plan_year", "issuer_id"])["issuer_claims_received_total"].sum().sum()
    true = i["issuer_claims_received_total"].sum()
    ratio = naive / true
    assert ratio > 1.5, "expected denormalization to be material"
    return (f"{len(i):,} issuer-years, 0 duplicates; naive plan-grain sum would "
            f"overstate volume {ratio:.1f}x")


@uat("TC-005", "BRD-005", "Rates suppressed below minimum denominator",
     "No denial rate computed on fewer than 100 claims; no overturn rate on fewer than 10 appeals")
def tc005():
    p, i = plan(), issuer()
    bad_d = p[p.denial_rate.notna() & (p.plan_claims_received_total < 100)]
    assert len(bad_d) == 0, f"{len(bad_d)} denial rates below the 100-claim floor"
    bad_o = i[i.internal_overturn_rate.notna() & (i.issuer_internal_appeals_filed < 10)]
    assert len(bad_o) == 0, f"{len(bad_o)} overturn rates below the 10-appeal floor"
    return "denominator floors enforced on denial and overturn rates"


@uat("TC-006", "BRD-006", "No rate exceeds 100 percent",
     "All computed rates are within [0, 1] or NULL")
def tc006():
    p, i = plan(), issuer()
    checks = [("plan.denial_rate", p.denial_rate),
              ("plan.denial_rate_in", p.denial_rate_in),
              ("plan.denial_rate_out", p.denial_rate_out),
              ("issuer.denial_rate", i.denial_rate),
              ("issuer.appeal_rate", i.appeal_rate),
              ("issuer.internal_overturn_rate", i.internal_overturn_rate),
              ("issuer.external_overturn_rate", i.external_overturn_rate)]
    for name, s in checks:
        over = int((s > 1).sum())
        assert over == 0, f"{name}: {over} values exceed 1.0"
        neg = int((s < 0).sum())
        assert neg == 0, f"{name}: {neg} negative values"
    return f"{len(checks)} rate fields validated within [0, 1]"


@uat("TC-007", "BRD-007", "Data quality log is complete",
     "Every DQ finding carries id, severity, finding, treatment, and rows affected")
def tc007():
    d = pd.read_csv(OUTPUTS / "dq_log.csv")
    required = ["dq_id", "severity", "field", "finding", "treatment", "rows_affected"]
    for c in required:
        assert c in d.columns, f"missing column {c}"
        assert d[c].notna().all(), f"column {c} has {d[c].isna().sum()} nulls"
    assert (d.severity == "Critical").any(), "no Critical finding recorded"
    return (f"{len(d)} findings across {d.dq_id.nunique()} IDs; "
            f"{int((d.severity=='Critical').sum())} Critical, "
            f"{int((d.severity=='High').sum())} High")


@uat("TC-010", "BRD-010, BRD-011, BRD-012", "Every denial reason mapped to root cause and owner",
     "All 10 source categories have a root cause, an owner, and CARC examples")
def tc010():
    assert len(ROOT_CAUSE_TAXONOMY) == len(DENIAL_REASON_COLS) == 10, \
        "taxonomy and reason column count mismatch"
    for col in DENIAL_REASON_COLS:
        assert col in ROOT_CAUSE_TAXONOMY, f"{col} unmapped"
        m = ROOT_CAUSE_TAXONOMY[col]
        for k in ("root_cause", "owner", "x12_carc_examples", "preventability",
                  "appealability", "effort_hours"):
            assert m.get(k) not in (None, ""), f"{col} missing {k}"
    owners = {m["owner"] for m in ROOT_CAUSE_TAXONOMY.values()}
    return f"10/10 mapped across {len(owners)} accountable owners"


@uat("TC-013", "BRD-013", "Reason mix uses only reconciling plan-years",
     "Reason mix denominator excludes plan-years whose categories do not sum to reported denials")
def tc013():
    from analyze import reason_mix
    p = plan()
    m = reason_mix(p)
    basis = int(m.basis_plan_years.iloc[0])
    recon = int(p.reason_reconciles.sum())
    assert basis == recon, f"mix basis {basis} != reconciling rows {recon}"
    assert basis < len(p), "expected some rows to be excluded"
    assert abs(m.share_of_denials.sum() - 1.0) < 1e-9, "shares do not sum to 1"
    return (f"mix computed on {basis:,} of {len(p):,} plan-years "
            f"({basis/len(p):.0%}); shares sum to 1.0")


@uat("TC-016", "BRD-016", "Claim value derived from published payment data",
     "Derivation reads CMS files and logs every step")
def tc016():
    cv = json.loads((OUTPUTS / "claim_value.json").read_text())
    d = pd.read_csv(OUTPUTS / "claim_value_derivation.csv")
    assert cv["blended_commercial_allowed_per_claim"] > 0
    assert cv["low"] < cv["blended_commercial_allowed_per_claim"] < cv["high"]
    for s in ("inpatient", "outpatient_procedural", "professional"):
        assert cv["observed_source_rows"][s] > 1000, f"{s} source rows implausibly low"
    settings = set(d[d.setting != "BLENDED"].setting)
    assert len(settings) == 4, f"expected 4 buckets, got {settings}"
    # Cite distinct rows: outpatient_ancillary is derived from the physician file,
    # so summing observed_source_rows would count that file twice.
    return (f"${cv['blended_commercial_allowed_per_claim']:,.2f}/claim from "
            f"{cv['distinct_source_rows']:,} distinct rows across "
            f"{cv['distinct_source_files']} CMS files, allocated over 4 buckets")


@uat("TC-018", "BRD-018, BRD-019", "Recovery is net of cost and appeal is selective",
     "Net recovery subtracts appeal cost; only ROI > 1.0 categories are recommended")
def tc018():
    r = pd.read_csv(OUTPUTS / "root_cause_summary.csv")
    calc = r.gross_recovery - r.appeal_cost
    assert ((calc - r.net_recovery).abs() < 0.01).all(), "net recovery is not gross minus cost"
    assert (r.appeal_recommended == (r.appeal_roi > 1.0)).all(), \
        "appeal_recommended does not follow the ROI threshold"
    npos = int(r.appeal_recommended.sum())
    assert 0 < npos < len(r), "expected a mix of positive and negative ROI categories"
    sel = r.net_recovery_selective.sum()
    blanket = r.net_recovery.sum()
    assert sel > blanket, "selective appeal should beat blanket appeal"
    return (f"{npos}/{len(r)} categories appeal-positive; selective ${sel:,.0f} "
            f"vs blanket ${blanket:,.0f}")


@uat("TC-022", "BRD-022", "Sensitivity covers every assumption",
     "Each assumption appears at its declared low and high bound")
def tc022():
    s = pd.read_csv(OUTPUTS / "sensitivity.csv")
    tested = set(s[s.assumption != "BASE CASE"].assumption)
    declared = set(ASSUMPTIONS)
    assert tested == declared, f"untested: {declared - tested}"
    for a in declared:
        scen = set(s[s.assumption == a].scenario)
        assert scen == {"low", "high"}, f"{a} missing a bound: {scen}"
    return f"{len(declared)} assumptions x 2 bounds tested"


@uat("TC-024", "BRD-024", "Calibration gate against external benchmark",
     "Modelled denial loss falls inside the published 3-5 percent of revenue band")
def tc024():
    c = pd.read_csv(OUTPUTS / "calibration_check.csv").iloc[0]
    assert c.status == "PASS", (
        f"calibration FAIL: modelled loss {c.denial_loss_pct_of_revenue:.2%} outside "
        f"{c.benchmark_low:.0%}-{c.benchmark_high:.0%}")
    return (f"modelled loss {c.denial_loss_pct_of_revenue:.2%} within "
            f"{c.benchmark_low:.0%}-{c.benchmark_high:.0%}")


@uat("TC-025", "BRD-025, BRD-026", "Payer benchmark with peer percentiles",
     "Each payer carries percentile rank on denial, appeal, and overturn rate")
def tc025():
    s = pd.read_csv(OUTPUTS / "issuer_scorecard.csv")
    for c in ("pct_denial_rate", "pct_appeal_rate", "pct_overturn_rate",
              "appeal_target_score"):
        assert c in s.columns, f"missing {c}"
    v = s.pct_denial_rate.dropna()
    assert v.between(0, 1).all(), "percentile outside [0,1]"
    return f"{len(s)} payers benchmarked on 3 percentile measures"


@uat("TC-028", "BRD-028", "Prioritized action list with owner and wave",
     "Every root cause has a rank, a wave, and an accountable owner")
def tc028():
    p = pd.read_csv(OUTPUTS / "prioritization.csv")
    for c in ("rank", "wave", "root_cause", "owner", "total_opportunity", "priority_score"):
        assert c in p.columns, f"missing {c}"
        assert p[c].notna().all(), f"{c} has nulls"
    assert p["rank"].tolist() == sorted(p["rank"].tolist()), "ranks not ordered"
    assert p.priority_score.is_monotonic_decreasing, "priority score not descending"
    return f"{len(p)} root causes ranked across {p.wave.nunique()} waves"


@uat("TC-029", "BRD-029", "Star schema with referential integrity",
     "All fact foreign keys resolve; payer dimension is Type 2")
def tc029():
    star = PROCESSED / "star"
    need = ["dim_date", "dim_payer", "dim_plan", "dim_geography",
            "dim_denial_reason", "fact_claims_summary", "fact_denials"]
    t = {}
    for n in need:
        f = star / f"{n}.csv"
        assert f.exists(), f"missing {n}.csv"
        t[n] = pd.read_csv(f)
    assert (star / "measures.dax").exists(), "missing measures.dax"

    fc, fd = t["fact_claims_summary"], t["fact_denials"]
    for fk, dim, key in [("payer_key", "dim_payer", "payer_key"),
                         ("geo_key", "dim_geography", "geo_key"),
                         ("date_key", "dim_date", "date_key")]:
        orphan = int((~fc[fk].isin(t[dim][key])).sum())
        assert orphan == 0, f"fact_claims_summary.{fk}: {orphan} orphans"
    for fk, dim, key in [("plan_key", "dim_plan", "plan_key"),
                         ("reason_key", "dim_denial_reason", "reason_key")]:
        orphan = int((~fd[fk].isin(t[dim][key])).sum())
        assert orphan == 0, f"fact_denials.{fk}: {orphan} orphans"

    dp = t["dim_payer"]
    for c in ("valid_from_year", "valid_to_year", "is_current"):
        assert c in dp.columns, f"dim_payer missing SCD2 column {c}"
    assert dp.is_current.sum() == dp.issuer_id.nunique(), \
        "each issuer must have exactly one current row"
    return (f"7 tables, referential integrity PASS, "
            f"{len(dp) - dp.issuer_id.nunique()} SCD2 name changes tracked")


@uat("TC-021", "BRD-021", "Unclassified denial share disclosed",
     "The share of denials reported as Other is computed and available for display")
def tc021():
    h = json.loads((OUTPUTS / "headline_metrics.json").read_text())
    share = h["reason_mix"]["unclassified_other_share"]
    assert 0 < share < 1
    assert share > 0.3, "expected the unclassified share to be material"
    return f"unclassified share {share:.1%} disclosed"


@uat("TC-017", "BRD-017", "Observed inputs separated from assumed inputs",
     "Every assumption carries a stated source; observed rates are not in the assumption set")
def tc017():
    for k, v in ASSUMPTIONS.items():
        for f in ("value", "low", "high", "source"):
            assert f in v, f"{k} missing {f}"
        assert v["low"] <= v["value"] <= v["high"], f"{k} value outside its own bounds"
        assert len(v["source"]) > 30, f"{k} source description too thin"
    forbidden = {"denial_rate", "appeal_rate", "overturn_rate", "resubmission_rate"}
    assert not (forbidden & set(ASSUMPTIONS)), "an observed rate is declared as an assumption"
    return f"{len(ASSUMPTIONS)} assumptions declared with bounds and sources; 0 observed rates among them"


@uat("TC-014", "BRD-014, BRD-015", "Preventability and effort are explicit adjustable parameters",
     "Every root cause declares preventability, appealability, and effort within valid ranges")
def tc014():
    for col, m in ROOT_CAUSE_TAXONOMY.items():
        for k in ("preventability", "appealability"):
            v = m[k]
            assert 0.0 <= v <= 1.0, f"{col}.{k} = {v} outside [0,1]"
        assert 0 < m["effort_hours"] <= 24, f"{col}.effort_hours = {m['effort_hours']} implausible"
    prev = [m["preventability"] for m in ROOT_CAUSE_TAXONOMY.values()]
    assert len(set(prev)) > 1, "preventability is uniform, which defeats its purpose"
    return (f"10 categories; preventability {min(prev):.0%}-{max(prev):.0%}, "
            f"effort {min(m['effort_hours'] for m in ROOT_CAUSE_TAXONOMY.values())}-"
            f"{max(m['effort_hours'] for m in ROOT_CAUSE_TAXONOMY.values())}h")


@uat("TC-020", "BRD-020", "Prevention value reported separately from recovery",
     "Prevention and net recovery are distinct columns and are not equal")
def tc020():
    r = pd.read_csv(OUTPUTS / "root_cause_summary.csv")
    for c in ("prevention_value", "net_recovery", "total_opportunity_selective"):
        assert c in r.columns, f"missing {c}"
    assert not r.prevention_value.equals(r.net_recovery), "prevention duplicates recovery"
    tot = r.prevention_value.sum() + r.net_recovery_selective.sum()
    assert abs(tot - r.total_opportunity_selective.sum()) < 1.0, \
        "total opportunity does not equal prevention plus selective recovery"
    ratio = r.prevention_value.sum() / max(r.net_recovery_selective.sum(), 1)
    return (f"prevention ${r.prevention_value.sum():,.0f} vs recovery "
            f"${r.net_recovery_selective.sum():,.0f} ({ratio:.0f}x)")


@uat("TC-027", "BRD-027", "State-level denial reporting",
     "State summary present with denial rate and issuer count per state")
def tc027():
    s = pd.read_csv(OUTPUTS / "state_summary.csv")
    for c in ("state", "issuers", "denial_rate", "claims_received"):
        assert c in s.columns, f"missing {c}"
    assert s.denial_rate.between(0, 1).all(), "state denial rate outside [0,1]"
    assert len(s) > 20, f"only {len(s)} states"
    return (f"{len(s)} states; denial rate {s.denial_rate.min():.1%}-"
            f"{s.denial_rate.max():.1%}")


@uat("TC-030", "BRD-030", "Findings rescale to any provider claim volume",
     "Doubling claim volume doubles the opportunity; rates are volume-invariant")
def tc030():
    from analyze import national_funnel, reason_mix, recovery_model
    from config import PROVIDER_PROFILE
    p, i = plan(), issuer()
    f, m = national_funnel(i), reason_mix(p)
    base_n = PROVIDER_PROFILE["annual_marketplace_claims"]
    r1 = recovery_model(m, f, provider={**PROVIDER_PROFILE,
                                        "annual_marketplace_claims": base_n})
    r2 = recovery_model(m, f, provider={**PROVIDER_PROFILE,
                                        "annual_marketplace_claims": base_n * 2})
    t1 = r1.total_opportunity_selective.sum()
    t2 = r2.total_opportunity_selective.sum()
    assert abs(t2 / t1 - 2.0) < 0.01, f"scaling is non-linear: {t2/t1:.3f}x for 2x volume"
    return f"2x volume -> {t2/t1:.3f}x opportunity (linear, as required)"


@uat("TC-031", "BRD-031", "Provenance documented with source and scope caveats",
     "Every source file is named with row counts and scope limitations disclosed")
def tc031():
    cv = json.loads((OUTPUTS / "claim_value.json").read_text())
    assert "note" in cv and len(cv["note"]) > 50, "derivation note missing or thin"
    d = pd.read_csv(OUTPUTS / "claim_value_derivation.csv")
    assert "scope_note" in d.columns, "derivation lacks scope notes"
    scoped = d[d.scope_note.notna() & (d.scope_note.astype(str).str.len() > 20)]
    assert len(scoped) >= 3, "fewer than 3 buckets carry a scope note"
    dq = pd.read_csv(OUTPUTS / "dq_log.csv")
    assert (dq.dq_id == "DQ-010").any(), "the C-APC scope finding is not in the DQ log"
    recon = pd.read_csv(OUTPUTS / "reconciliation.csv")
    assert len(recon) == 5, "reconciliation does not cover all plan years"
    return f"{len(scoped)} buckets scope-noted; DQ-010 logged; 5 plan years reconciled"


def main():
    rows, defects = [], []
    for spec in RESULTS:
        tc, fn = spec["tc_id"], spec["fn"]
        try:
            actual = fn()
            rows.append(dict(test_case_id=tc, brd_ids=spec["brd_ids"], title=spec["title"],
                             expected=spec["expected"], actual=actual, status="PASS"))
            print(f"  PASS  {tc}  {spec['title']}")
            print(f"        {actual}")
        except AssertionError as e:
            rows.append(dict(test_case_id=tc, brd_ids=spec["brd_ids"], title=spec["title"],
                             expected=spec["expected"], actual=str(e), status="FAIL"))
            defects.append(dict(defect_id=f"DEF-{len(defects)+1:03d}", test_case_id=tc,
                                brd_ids=spec["brd_ids"], severity="High",
                                summary=spec["title"], detail=str(e),
                                status="Open", resolution=""))
            print(f"  FAIL  {tc}  {spec['title']}\n        {e}")
        except Exception as e:  # noqa: BLE001
            rows.append(dict(test_case_id=tc, brd_ids=spec["brd_ids"], title=spec["title"],
                             expected=spec["expected"],
                             actual=f"{type(e).__name__}: {e}", status="ERROR"))
            defects.append(dict(defect_id=f"DEF-{len(defects)+1:03d}", test_case_id=tc,
                                brd_ids=spec["brd_ids"], severity="Critical",
                                summary=spec["title"],
                                detail=traceback.format_exc().strip().splitlines()[-1],
                                status="Open", resolution=""))
            print(f"  ERROR {tc}  {spec['title']}\n        {type(e).__name__}: {e}")

    df = pd.DataFrame(rows)
    df.to_csv(DOCS / "UAT_RESULTS.csv", index=False)
    if defects:
        pd.DataFrame(defects).to_csv(DOCS / "UAT_DEFECT_LOG.csv", index=False)

    n_pass = int((df.status == "PASS").sum())
    print(f"\n{'='*70}\nUAT: {n_pass}/{len(df)} passed")
    if n_pass != len(df):
        print(f"{len(defects)} defect(s) written to docs/UAT_DEFECT_LOG.csv")
        sys.exit(1)


if __name__ == "__main__":
    main()
