"""
Stage 02 - Harmonize five TC-PUF plan years into one canonical panel.

Three schema generations, inconsistent suppression handling, issuer-level values
denormalized across plan rows, and one header shipped with a stray double quote.
Every transformation is logged so a reviewer can reconcile the output row count
back to the source workbooks.

Outputs
    data/processed/plan_panel.parquet    plan-year grain
    data/processed/issuer_panel.parquet  issuer-year grain
    outputs/dq_log.csv                   data quality findings
    outputs/reconciliation.csv           source-to-target row reconciliation
"""
import warnings

import numpy as np
import pandas as pd

from config import (COLUMN_MAP, DENIAL_REASON_COLS, MIN_CLAIMS_FOR_RATE,
                    OUTPUTS, PLAN_YEARS, PROCESSED, PY_TO_EXPERIENCE_YEAR, RAW,
                    SCHEMA_GENERATION, SUPPRESSION_CODES)

warnings.simplefilter("ignore", UserWarning)

DQ = []       # data quality findings
RECON = []    # row-count reconciliation


def log_dq(dq_id, severity, plan_year, field, finding, treatment, rows_affected):
    DQ.append(dict(dq_id=dq_id, severity=severity, plan_year=plan_year, field=field,
                   finding=finding, treatment=treatment, rows_affected=rows_affected))


def find_header_row(path, sheet, probe=6):
    """Header row is the one containing a literal 'State' cell."""
    raw = pd.read_excel(path, sheet_name=sheet, header=None, nrows=probe)
    for i in range(len(raw)):
        if any(str(v).strip() == "State" for v in raw.iloc[i].tolist()):
            return i
    raise ValueError(f"No header row found in {path} :: {sheet}")


def clean_numeric(series, plan_year, field):
    """
    Split a CMS-suppressed column into (numeric value, suppression flag).

    Suppression markers must not collapse to zero. A '**' means the value exists
    but is withheld; scoring it as zero would understate denominators and inflate
    every denial rate computed from them.
    """
    s = series.astype(str).str.strip()
    flag = pd.Series(pd.NA, index=s.index, dtype="object")

    for code, label in SUPPRESSION_CODES.items():
        if code == "":
            mask = s.isin(["", "nan", "None", "NaN"])
        else:
            mask = s.str.upper() == code.upper()
        flag = flag.mask(mask, label)

    # Strip thousands separators, stray quotes, and percent signs before coercion.
    cleaned = (s.str.replace(",", "", regex=False)
                .str.replace("$", "", regex=False)
                .str.replace('"', "", regex=False)
                .str.replace("%", "", regex=False))
    val = pd.to_numeric(cleaned, errors="coerce")
    val = val.mask(flag.notna())  # suppressed stays NaN, never 0

    n_supp = int(flag.notna().sum())
    if n_supp:
        breakdown = flag.value_counts().to_dict()
        log_dq("DQ-001", "Medium", plan_year, field,
               f"{n_supp} rows carry CMS suppression markers {breakdown}",
               "Retained as NULL with a companion _flag column; excluded from rate denominators",
               n_supp)

    n_neg = int((val < 0).sum())
    if n_neg:
        log_dq("DQ-002", "High", plan_year, field,
               f"{n_neg} rows report a negative claim count",
               "Coerced to NULL; negative counts are not physically meaningful",
               n_neg)
        val = val.mask(val < 0)

    return val, flag


def load_year(plan_year):
    path = RAW / "tcpuf" / f"tcpuf_py{plan_year}.xlsx"
    gen = SCHEMA_GENERATION[plan_year]
    xl = pd.ExcelFile(path)
    sheet = [s for s in xl.sheet_names if "Ind QHP" in s][0]

    hr = find_header_row(path, sheet)
    df = pd.read_excel(path, sheet_name=sheet, header=hr)
    n_source = len(df)

    df.columns = [str(c).strip() for c in df.columns]

    # PY2024 ships Issuer_Claims_Denied_Out_of_Network with a trailing double
    # quote. Caught by the mapping, logged here so the defect is visible.
    typo = [c for c in df.columns if c.endswith('"')]
    if typo:
        log_dq("DQ-003", "High", plan_year, ", ".join(typo),
               "Source header contains a stray trailing double quote",
               "Mapped explicitly in config.COLUMN_MAP; a naive rename would drop the column",
               n_source)

    mapping = COLUMN_MAP[gen]
    unmapped = [c for c in df.columns if c not in mapping]
    df = df.rename(columns=mapping)
    df = df[[c for c in df.columns if c in set(mapping.values())]]

    # Drop the legend/footnote rows that trail the real data.
    df = df[df["issuer_id"].notna() & df["plan_id"].notna()].copy()
    n_after_footer = len(df)
    if n_source != n_after_footer:
        log_dq("DQ-004", "Low", plan_year, "issuer_id / plan_id",
               f"{n_source - n_after_footer} rows lack an issuer or plan identifier",
               "Dropped as legend/footnote rows, not data",
               n_source - n_after_footer)

    numeric_cols = [c for c in df.columns
                    if c.startswith(("issuer_claims", "plan_claims", "den_",
                                     "issuer_internal", "issuer_external",
                                     "avg_monthly"))]
    for c in numeric_cols:
        val, flag = clean_numeric(df[c], plan_year, c)
        df[c] = val
        df[c + "_flag"] = flag

    df["plan_year"] = plan_year
    df["experience_year"] = PY_TO_EXPERIENCE_YEAR[plan_year]
    df["schema_generation"] = gen

    # GEN1 has no network split; synthesize the canonical total columns so all
    # five years share one grain. Network-split columns stay NULL for GEN1,
    # which is honest: the data was never collected that way.
    for level in ("issuer", "plan"):
        for metric in ("received", "denied", "resubmitted"):
            tot = f"{level}_claims_{metric}_total"
            i_col, o_col = f"{level}_claims_{metric}_in", f"{level}_claims_{metric}_out"
            if tot not in df.columns:
                df[tot] = np.nan
            if i_col in df.columns and o_col in df.columns:
                derived = df[i_col].fillna(0) + df[o_col].fillna(0)
                derived = derived.mask(df[i_col].isna() & df[o_col].isna())
                df[tot] = df[tot].fillna(derived)
            else:
                df[i_col] = df.get(i_col, np.nan)
                df[o_col] = df.get(o_col, np.nan)

    for c in DENIAL_REASON_COLS:
        if c not in df.columns:
            df[c] = np.nan
            log_dq("DQ-005", "Medium", plan_year, c,
                   "Denial reason category absent from this schema generation",
                   "Filled as NULL; excluded from reason-mix denominators for this year",
                   n_after_footer)

    RECON.append(dict(plan_year=plan_year, schema_generation=gen,
                      source_rows=n_source, rows_after_footer_drop=n_after_footer,
                      unmapped_source_columns=len(unmapped),
                      unmapped_list="; ".join(unmapped) if unmapped else ""))
    return df


def build_plan_panel(frames):
    df = pd.concat(frames, ignore_index=True)

    df["plan_denials_classified"] = df[DENIAL_REASON_COLS].sum(axis=1, min_count=1)

    # Internal consistency: reason categories should sum to reported total denials.
    both = df["plan_denials_classified"].notna() & df["plan_claims_denied_total"].notna()
    gap = (df.loc[both, "plan_denials_classified"] - df.loc[both, "plan_claims_denied_total"])
    tol = 0.02 * df.loc[both, "plan_claims_denied_total"].clip(lower=1)
    n_bad = int((gap.abs() > tol).sum())
    if n_bad:
        log_dq("DQ-006", "High", "all", "plan_denials_classified vs plan_claims_denied_total",
               f"{n_bad} plan-years where reason categories do not reconcile to reported "
               f"total denials within 2 percent",
               "Flagged via reason_reconciles=False; reason-mix analysis uses only "
               "reconciling rows, volume analysis uses all rows",
               n_bad)
    df["reason_reconciles"] = False
    df.loc[both, "reason_reconciles"] = (gap.abs() <= tol).values

    df["denial_rate"] = np.where(
        df["plan_claims_received_total"] >= MIN_CLAIMS_FOR_RATE,
        df["plan_claims_denied_total"] / df["plan_claims_received_total"], np.nan)

    n_impossible = int((df["denial_rate"] > 1).sum())
    if n_impossible:
        log_dq("DQ-007", "High", "all", "denial_rate",
               f"{n_impossible} plan-years report more denials than claims received",
               "Coerced to NULL; a rate above 100 percent indicates a source reporting error",
               n_impossible)
        df.loc[df["denial_rate"] > 1, "denial_rate"] = np.nan

    df["denial_rate_in"] = np.where(
        df["plan_claims_received_in"] >= MIN_CLAIMS_FOR_RATE,
        df["plan_claims_denied_in"] / df["plan_claims_received_in"], np.nan)
    df["denial_rate_out"] = np.where(
        df["plan_claims_received_out"] >= MIN_CLAIMS_FOR_RATE,
        df["plan_claims_denied_out"] / df["plan_claims_received_out"], np.nan)
    for c in ("denial_rate_in", "denial_rate_out"):
        df.loc[df[c] > 1, c] = np.nan

    df["state"] = df["state"].astype(str).str.strip().str.upper()
    df["issuer_id"] = pd.to_numeric(df["issuer_id"], errors="coerce").astype("Int64")
    df["metal_level"] = df["metal_level"].astype(str).str.strip().str.title()
    df["plan_type"] = df["plan_type"].astype(str).str.strip().str.upper()

    dupes = df.duplicated(subset=["plan_year", "plan_id"], keep=False).sum()
    if dupes:
        log_dq("DQ-008", "Medium", "all", "plan_year + plan_id",
               f"{dupes} rows share a plan_year/plan_id key",
               "Aggregated to one row per plan-year by summing claim counts",
               int(dupes))
    return df


def build_issuer_panel(plan_df):
    """
    Issuer-level metrics are denormalized across every plan row belonging to that
    issuer. Summing them would multiply each issuer's volume by its plan count.
    Deduplicate to issuer-year grain first, then take the single reported value.
    """
    issuer_cols = [c for c in plan_df.columns
                   if c.startswith(("issuer_claims", "issuer_internal", "issuer_external"))
                   and not c.endswith("_flag")]
    keys = ["plan_year", "experience_year", "issuer_id", "issuer_name", "state",
            "schema_generation"]

    naive_sum = plan_df.groupby(["plan_year", "issuer_id"])["issuer_claims_received_total"].sum().sum()

    iss = plan_df[keys + issuer_cols].drop_duplicates(subset=["plan_year", "issuer_id"])
    true_total = iss["issuer_claims_received_total"].sum()

    log_dq("DQ-009", "Critical", "all", "issuer_claims_* (denormalization)",
           f"Issuer-level values repeat across all plan rows. Naive summation yields "
           f"{naive_sum:,.0f} claims against a true {true_total:,.0f}, a "
           f"{naive_sum / max(true_total, 1):.1f}x overstatement",
           "Deduplicated to issuer-year grain before any issuer-level aggregation",
           len(plan_df))

    plan_roll = (plan_df.groupby(["plan_year", "issuer_id"], as_index=False)
                 .agg(plan_count=("plan_id", "nunique"),
                      plan_claims_received=("plan_claims_received_total", "sum"),
                      plan_claims_denied=("plan_claims_denied_total", "sum"),
                      **{c: (c, "sum") for c in DENIAL_REASON_COLS}))

    iss = iss.merge(plan_roll, on=["plan_year", "issuer_id"], how="left")

    iss["denial_rate"] = np.where(
        iss["issuer_claims_received_total"] >= MIN_CLAIMS_FOR_RATE,
        iss["issuer_claims_denied_total"] / iss["issuer_claims_received_total"], np.nan)
    iss.loc[iss["denial_rate"] > 1, "denial_rate"] = np.nan

    # The appeal funnel. These three rates are the analytical core of the project.
    iss["appeal_rate"] = np.where(
        iss["issuer_claims_denied_total"] >= MIN_CLAIMS_FOR_RATE,
        iss["issuer_internal_appeals_filed"] / iss["issuer_claims_denied_total"], np.nan)
    iss["internal_overturn_rate"] = np.where(
        iss["issuer_internal_appeals_filed"] >= 10,
        iss["issuer_internal_appeals_overturned"] / iss["issuer_internal_appeals_filed"], np.nan)
    iss["external_overturn_rate"] = np.where(
        iss["issuer_external_appeals_filed"] >= 10,
        iss["issuer_external_appeals_overturned"] / iss["issuer_external_appeals_filed"], np.nan)
    for c in ("appeal_rate", "internal_overturn_rate", "external_overturn_rate"):
        iss.loc[iss[c] > 1, c] = np.nan

    return iss


def main():
    frames = [load_year(y) for y in PLAN_YEARS]
    plan_df = build_plan_panel(frames)
    issuer_df = build_issuer_panel(plan_df)

    plan_df.to_parquet(PROCESSED / "plan_panel.parquet", index=False)
    issuer_df.to_parquet(PROCESSED / "issuer_panel.parquet", index=False)

    dq = pd.DataFrame(DQ).sort_values(
        ["severity", "dq_id"],
        key=lambda s: s.map({"Critical": 0, "High": 1, "Medium": 2, "Low": 3}).fillna(9)
        if s.name == "severity" else s)
    dq.to_csv(OUTPUTS / "dq_log.csv", index=False)
    pd.DataFrame(RECON).to_csv(OUTPUTS / "reconciliation.csv", index=False)

    print(f"plan panel   : {len(plan_df):,} plan-years  "
          f"({plan_df['plan_id'].nunique():,} distinct plans)")
    print(f"issuer panel : {len(issuer_df):,} issuer-years "
          f"({issuer_df['issuer_id'].nunique():,} distinct issuers)")
    print(f"states       : {plan_df['state'].nunique()}")
    print(f"DQ findings  : {len(dq)}  "
          f"(Critical {sum(dq.severity == 'Critical')}, High {sum(dq.severity == 'High')})")
    print(f"\ntotal claims received (issuer grain): "
          f"{issuer_df['issuer_claims_received_total'].sum():,.0f}")
    print(f"total claims denied   (issuer grain): "
          f"{issuer_df['issuer_claims_denied_total'].sum():,.0f}")


if __name__ == "__main__":
    main()
