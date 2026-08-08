"""
Generate docs/DATA_DICTIONARY.md from the live mapping configuration and the
harmonized panels.

A hand-typed data dictionary is wrong the first time someone renames a column.
This reads config.COLUMN_MAP and the actual parquet schemas, so the document and
the code cannot disagree.
"""
from pathlib import Path

import pandas as pd

from config import (ASSUMPTIONS, COLUMN_MAP, DENIAL_REASON_COLS, OUTPUTS,
                    PLAN_YEARS, PROCESSED, PROVIDER_PROFILE, ROOT_CAUSE_TAXONOMY,
                    SCHEMA_GENERATION)

DOCS = Path(__file__).resolve().parents[1] / "docs"

FIELD_NOTES = {
    "issuer_claims_received_total": "Issuer-level. Denormalized across plan rows in source; deduplicated to issuer grain.",
    "issuer_claims_denied_total": "Issuer-level. Denominator for the appeal rate.",
    "issuer_internal_appeals_filed": "Issuer-level. Numerator for the appeal rate.",
    "issuer_internal_appeals_overturned": "Issuer-level. Numerator for the overturn rate; the observed recovery probability.",
    "plan_claims_received_total": "Plan-level. GEN1 reports directly; GEN2/GEN3 derived as in-network + out-of-network.",
    "plan_claims_denied_total": "Plan-level. Reconciliation target for the ten reason categories.",
    "denial_rate": "Derived. NULL where claims received < 100.",
    "appeal_rate": "Derived. Appeals filed / claims denied.",
    "internal_overturn_rate": "Derived. NULL where appeals filed < 10.",
    "reason_reconciles": "Derived flag. True where reason categories sum to reported total denials within 2%.",
    "schema_generation": "Derived. GEN1 = PY2022-23, GEN2 = PY2024, GEN3 = PY2025-26.",
    "experience_year": "Derived. Plan year minus 2; the year the claims experience occurred.",
}


def source_to_target():
    rows = []
    for gen, mapping in COLUMN_MAP.items():
        years = [y for y, g in SCHEMA_GENERATION.items() if g == gen]
        for src, tgt in mapping.items():
            rows.append(dict(schema_generation=gen,
                             plan_years=", ".join(str(y) for y in years),
                             source_column=src, canonical_field=tgt))
    df = pd.DataFrame(rows)
    piv = (df.groupby("canonical_field")
             .apply(lambda g: pd.Series({
                 "GEN1 (PY2022-23)": " / ".join(sorted(set(g[g.schema_generation == "GEN1"].source_column))) or "—",
                 "GEN2 (PY2024)": " / ".join(sorted(set(g[g.schema_generation == "GEN2"].source_column))) or "—",
                 "GEN3 (PY2025-26)": " / ".join(sorted(set(g[g.schema_generation == "GEN3"].source_column))) or "—",
             }), include_groups=False)
             .reset_index())
    return piv.sort_values("canonical_field")


def schema_table(path, title):
    df = pd.read_parquet(path)
    rows = []
    for c in df.columns:
        if c.endswith("_flag"):
            continue
        s = df[c]
        rows.append(dict(
            field=c, dtype=str(s.dtype),
            populated=f"{s.notna().mean():.0%}",
            note=FIELD_NOTES.get(c, "")))
    return pd.DataFrame(rows), len(df), title


def md_table(df):
    head = "| " + " | ".join(df.columns) + " |"
    sep = "|" + "|".join(["---"] * len(df.columns)) + "|"
    body = "\n".join("| " + " | ".join(str(v).replace("|", "\\|") for v in r) + " |"
                     for r in df.itertuples(index=False))
    return f"{head}\n{sep}\n{body}"


def main():
    plan = pd.read_parquet(PROCESSED / "plan_panel.parquet")
    iss = pd.read_parquet(PROCESSED / "issuer_panel.parquet")
    recon = pd.read_csv(OUTPUTS / "reconciliation.csv")

    s2t = source_to_target()
    plan_schema, n_plan, _ = schema_table(PROCESSED / "plan_panel.parquet", "plan")
    iss_schema, n_iss, _ = schema_table(PROCESSED / "issuer_panel.parquet", "issuer")

    tax = pd.DataFrame(ROOT_CAUSE_TAXONOMY).T.reset_index().rename(
        columns={"index": "canonical_field", "root_cause": "RCM root cause",
                 "owner": "Accountable owner", "x12_carc_examples": "CARC examples",
                 "preventability": "Preventability", "appealability": "Appealability",
                 "effort_hours": "Effort (hrs)"})

    asm = pd.DataFrame([
        dict(assumption=k, base=v["value"], low=v["low"], high=v["high"],
             source=v["source"]) for k, v in ASSUMPTIONS.items()])

    doc = f"""# Data Dictionary

Document ID: DD-RCM-DEN-001 · Companion to `BRD.md`

> **This file is generated** by `src/generate_data_dictionary.py` from the live
> mapping configuration and the harmonized panel schemas. Do not edit by hand — a
> hand-maintained dictionary is wrong the first time a column is renamed. Regenerate
> after any change to `src/config.py`.

---

## 1. Sources

| Source | Publisher | Vintage | Grain | Rows used | Nature |
|---|---|---|---|---|---|
| Transparency in Coverage PUF | CMS / CCIIO, `data.healthcare.gov` | Plan years {min(PLAN_YEARS)}–{max(PLAN_YEARS)} | Issuer and plan | {len(plan):,} plan-years | Payer self-reported, unaudited |
| Medicare Inpatient Hospitals by Provider and Service | CMS, `data.cms.gov` | DY2024 | Provider × DRG | 145,879 | Published payment data |
| Medicare Outpatient Hospitals by Provider and Service | CMS, `data.cms.gov` | DY2024 | Provider × APC | 63,518 | Published payment data, **C-APC only** |
| Medicare Physician & Other Practitioners by Provider | CMS, `data.cms.gov` | DY2024 | Provider | 1,296,739 | Published payment data |

**No protected health information is used anywhere in this project.** Every source is
a public aggregate file. There is no patient-level record at any stage.

### Scope limitations

- TC-PUF covers **federally-facilitated Exchange plans only**. States running their own
  Exchange do not report to this file, so {plan['state'].nunique()} states are represented, not 50.
- TC-PUF is **payer self-reported and unaudited**. Internal consistency problems are
  documented in `outputs/dq_log.csv`.
- TC-PUF reports **claim counts, not dollars**. All monetization is derived; see §6.
- The CMS outpatient file covers **Comprehensive APCs only** — 72 procedural APC groups,
  68 of which carry a priced row. It excludes routine outpatient volume. See DQ-010 and defect DEF-001.
- Data carries a **two-year lag**: the PY{max(PLAN_YEARS)} file reports CY{max(PLAN_YEARS)-2} experience.

---

## 2. Source-to-target mapping

Three schema generations map to one canonical model. An em dash means the field does
not exist in that generation, which is recorded rather than silently filled.

{md_table(s2t)}

### Schema generation notes

- **GEN1 (PY2022–PY2023)** reports claims received and denied as totals with no
  in-network / out-of-network split. The split fields stay NULL for these years rather
  than being imputed.
- **GEN2 (PY2024)** introduces the network split. It also ships
  `Issuer_Claims_Denied_Out_of_Network` with a **trailing double quote** in the header.
  Both spellings are mapped explicitly. See defect DEF-005.
- **GEN3 (PY2025–PY2026)** renames the enrollment fields and adds `Exchange_Type` and
  `Individual/SHOP`.

---

## 3. Suppression handling

CMS uses markers rather than nulls. Reading them as zero would inflate every rate
computed from the affected denominator, so each is preserved as a distinct state in a
companion `_flag` column.

| Marker | Meaning | Treatment |
|---|---|---|
| `*` | Data not available for this issuer/plan | NULL + flag `not_available` |
| `**` | Suppressed due to small cell size | NULL + flag `suppressed_small_cell` |
| `***` | Not required due to plan type | NULL + flag `not_required` |
| `N/A` | Issuer or plan is new to the Exchange | NULL + flag `not_applicable` |

---

## 4. Canonical schema — plan panel

`data/processed/plan_panel.parquet` · grain: one row per plan per plan year · {n_plan:,} rows

{md_table(plan_schema)}

---

## 5. Canonical schema — issuer panel

`data/processed/issuer_panel.parquet` · grain: one row per issuer per plan year · {n_iss:,} rows

> Issuer-level measures are denormalized across every plan row in the source. Summing
> them at plan grain overstates national volume **84x**. This panel is deduplicated to
> issuer grain before any aggregation. See DQ-009 and defect DEF-004.

{md_table(iss_schema)}

---

## 6. Denial root-cause taxonomy

Maps each payer-reported denial reason to the revenue cycle stage that originates it
and the department accountable for preventing it.

{md_table(tax[["canonical_field", "RCM root cause", "Accountable owner", "CARC examples",
               "Preventability", "Appealability", "Effort (hrs)"]])}

`Preventability`, `Appealability`, and `Effort (hrs)` are **assumptions** carrying RCM
domain judgement, not observed values. All three are adjustable and flow into the
sensitivity analysis.

---

## 7. Model assumptions

Everything not in this table is observed from source data.

{md_table(asm)}

### Reference provider

{PROVIDER_PROFILE['description']} · {PROVIDER_PROFILE['annual_marketplace_claims']:,} annual
marketplace claims. All findings are expressed as rates and rescale linearly to any
claim volume, verified by test case TC-030.

---

## 8. Row reconciliation

Source workbook through to harmonized panel.

{md_table(recon[["plan_year", "schema_generation", "source_rows",
                 "rows_after_footer_drop", "unmapped_source_columns"]])}

---

## 9. Star schema

`data/processed/star/` — Kimball dimensional model for Power BI.

| Table | Grain | Type |
|---|---|---|
| `dim_date` | Experience year | Conformed dimension |
| `dim_payer` | Issuer × validity period | **Type 2 SCD** on issuer name |
| `dim_plan` | Plan | Dimension |
| `dim_geography` | State | Conformed dimension |
| `dim_denial_reason` | Denial reason | Dimension with root cause and owner |
| `fact_claims_summary` | Issuer × year | Fact |
| `fact_denials` | Plan × year × reason | Fact |

`dim_payer` is Type 2 because issuer names change across plan years while the issuer ID
persists. Denial history must stay attached to the name in force at the time.
`measures.dax` carries the DAX measure definitions and the relationship list.
"""
    (DOCS / "DATA_DICTIONARY.md").write_text(doc, encoding="utf-8")
    print(f"docs/DATA_DICTIONARY.md written")
    print(f"  source-to-target rows : {len(s2t)}")
    print(f"  plan panel fields     : {len(plan_schema)}")
    print(f"  issuer panel fields   : {len(iss_schema)}")


if __name__ == "__main__":
    main()
