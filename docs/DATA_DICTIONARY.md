# Data Dictionary

Document ID: DD-RCM-DEN-001 · Companion to `BRD.md`

> **This file is generated** by `src/generate_data_dictionary.py` from the live
> mapping configuration and the harmonized panel schemas. Do not edit by hand — a
> hand-maintained dictionary is wrong the first time a column is renamed. Regenerate
> after any change to `src/config.py`.

---

## 1. Sources

| Source | Publisher | Vintage | Grain | Rows used | Nature |
|---|---|---|---|---|---|
| Transparency in Coverage PUF | CMS / CCIIO, `data.healthcare.gov` | Plan years 2022–2026 | Issuer and plan | 25,666 plan-years | Payer self-reported, unaudited |
| Medicare Inpatient Hospitals by Provider and Service | CMS, `data.cms.gov` | DY2024 | Provider × DRG | 145,879 | Published payment data |
| Medicare Outpatient Hospitals by Provider and Service | CMS, `data.cms.gov` | DY2024 | Provider × APC | 63,518 | Published payment data, **C-APC only** |
| Medicare Physician & Other Practitioners by Provider | CMS, `data.cms.gov` | DY2024 | Provider | 1,296,739 | Published payment data |

**No protected health information is used anywhere in this project.** Every source is
a public aggregate file. There is no patient-level record at any stage.

### Scope limitations

- TC-PUF covers **federally-facilitated Exchange plans only**. States running their own
  Exchange do not report to this file, so 33 states are represented, not 50.
- TC-PUF is **payer self-reported and unaudited**. Internal consistency problems are
  documented in `outputs/dq_log.csv`.
- TC-PUF reports **claim counts, not dollars**. All monetization is derived; see §6.
- The CMS outpatient file covers **Comprehensive APCs only** — 72 procedural APC groups,
  68 of which carry a priced row. It excludes routine outpatient volume. See DQ-010 and defect DEF-001.
- Data carries a **two-year lag**: the PY2026 file reports CY2024 experience.

---

## 2. Source-to-target mapping

Three schema generations map to one canonical model. An em dash means the field does
not exist in that generation, which is recorded rather than silently filled.

| canonical_field | GEN1 (PY2022-23) | GEN2 (PY2024) | GEN3 (PY2025-26) |
|---|---|---|---|
| avg_monthly_disenrollment | Disenrollment_Data | Disenrollment_Data | Average Monthly Disenrollment |
| avg_monthly_enrollment | Enrollment_Data | Enrollment_Data | Average Monthly Enrollment |
| den_administrative | Plan_Number_Claims_Denied_Due_To_Administrative_Reason | Plan_Number_Claims_Denied_Due_To_Administrative_Reason | Plan_Number_Claims_Denied_Due_To_Administrative_Reason |
| den_benefit_limit | Plan_Number_Claims_Denied_Due_To_Enrolle_Benefit_Limit_Reached | Plan_Number_Claims_Denied_Due_To_Enrolle_Benefit_Limit_Reached | Plan_Number_Claims_Denied_Due_To_Enrolle_Benefit_Limit_Reached |
| den_investigational | Plan_Number_Claims_Denied_Due_To_Investigational_Experimental_Cosmetic_Proceduce | Plan_Number_Claims_Denied_Due_To_Investigational_Experimental_Cosmetic_Proceduce | Plan_Number_Claims_Denied_Due_To_Investigational_Experimental_Cosmetic_Proceduce |
| den_med_nec_behavioral | Plan_Number_Claims_Denied_Not_Medically_Necessary_Behavioral_Health_Only | Plan_Number_Claims_Denied_Not_Medically_Necessary_Behavioral_Health_Only | Plan_Number_Claims_Denied_Not_Medically_Necessary_Behavioral_Health_Only |
| den_med_nec_other | Plan_Number_Claims_Denied_Not_Medically_Necessary_Excl_Behavioral_Health | Plan_Number_Claims_Denied_Not_Medically_Necessary_Excl_Behavioral_Health | Plan_Number_Claims_Denied_Not_Medically_Necessary_Excluding_Behavioral_Health |
| den_member_not_covered | Plan_Number_Claims_Denied_Due_To_Member_Not_Covered | Plan_Number_Claims_Denied_Due_To_Member_Not_Covered | Plan_Number_Claims_Denied_Due_To_Member_Not_Covered |
| den_other | Plan_Number_Claims_Denied_Other | Plan_Number_Claims_Denied_Other | Plan_Number_Claims_Denied_Other |
| den_out_of_network | Plan_Number_Claims_Denied_Due_To_Out_Of_Network | Plan_Number_Claims_Denied_Due_To_Out_Of_Network | Plan_Number_Claims_Denied_Due_To_Out_Of_Network |
| den_referral_required | Plan_Number_Claims_Denied_Referral_Required | Plan_Number_Claims_Denied_Referral_Required | Plan_Number_Claims_Denied_Referral_Required |
| den_service_excluded | Plan_Number_Claims_Denied_Services_Excluded | Plan_Number_Claims_Denied_Services_Excluded | Plan_Number_Claims_Denied_Services_Excluded |
| exchange_type | — | — | Exchange_Type |
| issuer_claims_denied_in | — | Issuer_Claims_Denied_In_Network | Issuer_Claims_Denied_In_Network |
| issuer_claims_denied_out | — | Issuer_Claims_Denied_Out_of_Network / Issuer_Claims_Denied_Out_of_Network" | Issuer_Claims_Denied_Out_of_Network |
| issuer_claims_denied_total | Issuer_Claims_Denials | — | — |
| issuer_claims_received_in | — | Issuer_Claims_Received_In_Network | Issuer_Claims_Received_In_Network |
| issuer_claims_received_out | — | Issuer_Claims_Received_Out_of_Network | Issuer_Claims_Received_Out_of_Network |
| issuer_claims_received_total | Issuer_Claims_Received | — | — |
| issuer_claims_resubmitted_in | — | Issuer_Claims_Resubmitted_In_Network | Issuer_Claims_Resubmitted_In_Network |
| issuer_claims_resubmitted_out | — | Issuer_Claims_Resubmitted_Out_of_Network | Issuer_Claims_Resubmitted_Out_of_Network |
| issuer_external_appeals_filed | Issuer_External_Appeals_Filed | Issuer_External_Appeals_Filed | Issuer_External_Appeals_Filed |
| issuer_external_appeals_overturned | Issuer_Number_External_Appeals_Overturned | Issuer_Number_External_Appeals_Overturned | Issuer_Number_External_Appeals_Overturned |
| issuer_id | Issuer_ID | Issuer_ID | Issuer_ID |
| issuer_internal_appeals_filed | Issuer_Internal_Appeals_Filed | Issuer_Internal_Appeals_Filed | Issuer_Internal_Appeals_Filed |
| issuer_internal_appeals_overturned | Issuer_Number_Internal_Appeals_Overturned | Issuer_Number_Internal_Appeals_Overturned | Issuer_Number_Internal_Appeals_Overturned |
| issuer_name | Issuer_Name | Issuer_Name | Issuer_Name |
| issuer_new_to_exchange | Is_Issuer_New_to_Exchange? (Yes_or_No) | Is_Issuer_New_to_Exchange?(Yes_or_No) | Is_Issuer_New_to_Exchange?(Yes_or_No) |
| market | — | — | Individual/SHOP |
| metal_level | Metal_Level | Metal_Level | Metal_Level |
| plan_claims_denied_in | — | Plan_Number_Claims_Denied_In_Network | Plan_Number_Claims_Denied_In_Network |
| plan_claims_denied_out | — | Plan_Number_Claims_Denied_Out_of_Network | Plan_Number_Claims_Denied_Out_of_Network |
| plan_claims_denied_total | Plan_Number_Claims_Denied | — | — |
| plan_claims_received_in | — | Plan_Number_Claims_Received_In_Network | Plan_Number_Claims_Received_In_Network |
| plan_claims_received_out | — | Plan_Number_Claims_Received_Out_of_Network | Plan_Number_Claims_Received_Out_of_Network |
| plan_claims_received_total | Plan_Number_Claims_Received | — | — |
| plan_claims_resubmitted_in | — | Plan_Number_Claims_Resubmitted_In_Network | Plan_Number_Claims_Resubmitted_In_Network |
| plan_claims_resubmitted_out | — | Plan_Number_Claims_Resubmitted_Out_of_Network | Plan_Number_Claims_Resubmitted_Out_of_Network |
| plan_id | Plan_ID | Plan_ID | Plan_ID |
| plan_new_or_returning | — | New_or_Returning_Plan | — |
| plan_type | Plan_Type | Plan_Type | Plan_Type |
| product_type | QHP/SADP | QHP or SADP? | QHP or SADP? |
| sadp_only | SADP_Only? | SADP_Only | SADP_Only |
| state | State | State | State |
| url_claims_policy | URL_Claims_Payment_Policies | URL_Claims_Payment_Policies | URL_Claims_Payment_Policies |

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

`data/processed/plan_panel.parquet` · grain: one row per plan per plan year · 25,666 rows

| field | dtype | populated | note |
|---|---|---|---|
| state | str | 100% |  |
| issuer_name | str | 100% |  |
| issuer_id | Int64 | 100% |  |
| issuer_new_to_exchange | str | 100% |  |
| sadp_only | str | 100% |  |
| plan_id | str | 100% |  |
| product_type | str | 100% |  |
| plan_type | str | 100% |  |
| metal_level | str | 100% |  |
| url_claims_policy | str | 100% |  |
| issuer_claims_received_total | float64 | 87% | Issuer-level. Denormalized across plan rows in source; deduplicated to issuer grain. |
| issuer_claims_denied_total | float64 | 87% | Issuer-level. Denominator for the appeal rate. |
| issuer_internal_appeals_filed | float64 | 84% | Issuer-level. Numerator for the appeal rate. |
| issuer_internal_appeals_overturned | float64 | 81% | Issuer-level. Numerator for the overturn rate; the observed recovery probability. |
| issuer_external_appeals_filed | float64 | 56% |  |
| issuer_external_appeals_overturned | float64 | 53% |  |
| plan_claims_received_total | float64 | 43% | Plan-level. GEN1 reports directly; GEN2/GEN3 derived as in-network + out-of-network. |
| plan_claims_denied_total | float64 | 42% | Plan-level. Reconciliation target for the ten reason categories. |
| den_referral_required | float64 | 39% |  |
| den_service_excluded | float64 | 39% |  |
| den_med_nec_other | float64 | 29% |  |
| den_med_nec_behavioral | float64 | 32% |  |
| den_other | float64 | 41% |  |
| avg_monthly_enrollment | float64 | 31% |  |
| avg_monthly_disenrollment | float64 | 26% |  |
| plan_year | int64 | 100% |  |
| experience_year | int64 | 100% | Derived. Plan year minus 2; the year the claims experience occurred. |
| schema_generation | str | 100% | Derived. GEN1 = PY2022-23, GEN2 = PY2024, GEN3 = PY2025-26. |
| issuer_claims_received_in | float64 | 49% |  |
| issuer_claims_received_out | float64 | 49% |  |
| issuer_claims_denied_in | float64 | 49% |  |
| issuer_claims_denied_out | float64 | 49% |  |
| issuer_claims_resubmitted_total | float64 | 49% |  |
| issuer_claims_resubmitted_in | float64 | 49% |  |
| issuer_claims_resubmitted_out | float64 | 48% |  |
| plan_claims_received_in | float64 | 27% |  |
| plan_claims_received_out | float64 | 26% |  |
| plan_claims_denied_in | float64 | 26% |  |
| plan_claims_denied_out | float64 | 25% |  |
| plan_claims_resubmitted_total | float64 | 26% |  |
| plan_claims_resubmitted_in | float64 | 25% |  |
| plan_claims_resubmitted_out | float64 | 21% |  |
| den_out_of_network | float64 | 23% |  |
| den_benefit_limit | float64 | 22% |  |
| den_member_not_covered | float64 | 23% |  |
| den_investigational | float64 | 17% |  |
| den_administrative | float64 | 25% |  |
| plan_new_or_returning | str | 20% |  |
| market | str | 34% |  |
| exchange_type | str | 34% |  |
| plan_denials_classified | float64 | 43% |  |
| reason_reconciles | bool | 100% | Derived flag. True where reason categories sum to reported total denials within 2%. |
| denial_rate | float64 | 42% | Derived. NULL where claims received < 100. |
| denial_rate_in | float64 | 26% |  |
| denial_rate_out | float64 | 22% |  |

---

## 5. Canonical schema — issuer panel

`data/processed/issuer_panel.parquet` · grain: one row per issuer per plan year · 1,043 rows

> Issuer-level measures are denormalized across every plan row in the source. Summing
> them at plan grain overstates national volume **84x**. This panel is deduplicated to
> issuer grain before any aggregation. See DQ-009 and defect DEF-004.

| field | dtype | populated | note |
|---|---|---|---|
| plan_year | int64 | 100% |  |
| experience_year | int64 | 100% | Derived. Plan year minus 2; the year the claims experience occurred. |
| issuer_id | Int64 | 100% |  |
| issuer_name | str | 100% |  |
| state | str | 100% |  |
| schema_generation | str | 100% | Derived. GEN1 = PY2022-23, GEN2 = PY2024, GEN3 = PY2025-26. |
| issuer_claims_received_total | float64 | 79% | Issuer-level. Denormalized across plan rows in source; deduplicated to issuer grain. |
| issuer_claims_denied_total | float64 | 79% | Issuer-level. Denominator for the appeal rate. |
| issuer_internal_appeals_filed | float64 | 73% | Issuer-level. Numerator for the appeal rate. |
| issuer_internal_appeals_overturned | float64 | 68% | Issuer-level. Numerator for the overturn rate; the observed recovery probability. |
| issuer_external_appeals_filed | float64 | 42% |  |
| issuer_external_appeals_overturned | float64 | 41% |  |
| issuer_claims_received_in | float64 | 49% |  |
| issuer_claims_received_out | float64 | 49% |  |
| issuer_claims_denied_in | float64 | 49% |  |
| issuer_claims_denied_out | float64 | 49% |  |
| issuer_claims_resubmitted_total | float64 | 49% |  |
| issuer_claims_resubmitted_in | float64 | 48% |  |
| issuer_claims_resubmitted_out | float64 | 47% |  |
| plan_count | int64 | 100% |  |
| plan_claims_received | float64 | 100% |  |
| plan_claims_denied | float64 | 100% |  |
| den_referral_required | float64 | 100% |  |
| den_out_of_network | float64 | 100% |  |
| den_service_excluded | float64 | 100% |  |
| den_med_nec_other | float64 | 100% |  |
| den_med_nec_behavioral | float64 | 100% |  |
| den_benefit_limit | float64 | 100% |  |
| den_member_not_covered | float64 | 100% |  |
| den_investigational | float64 | 100% |  |
| den_administrative | float64 | 100% |  |
| den_other | float64 | 100% |  |
| denial_rate | float64 | 78% | Derived. NULL where claims received < 100. |
| appeal_rate | float64 | 72% | Derived. Appeals filed / claims denied. |
| internal_overturn_rate | float64 | 66% | Derived. NULL where appeals filed < 10. |
| external_overturn_rate | float64 | 11% |  |

---

## 6. Denial root-cause taxonomy

Maps each payer-reported denial reason to the revenue cycle stage that originates it
and the department accountable for preventing it.

| canonical_field | RCM root cause | Accountable owner | CARC examples | Preventability | Appealability | Effort (hrs) |
|---|---|---|---|---|---|---|
| den_referral_required | Front-End: Authorization & Referral | Patient Access | CARC 15, 197 | 0.85 | 0.55 | 1.0 |
| den_out_of_network | Front-End: Eligibility & Network Verification | Patient Access | CARC 242, 243 | 0.7 | 0.3 | 1.5 |
| den_member_not_covered | Front-End: Eligibility & Network Verification | Patient Access | CARC 27, 31 | 0.9 | 0.25 | 0.5 |
| den_med_nec_other | Clinical: Medical Necessity | Clinical Documentation Improvement | CARC 50, 55 | 0.45 | 0.75 | 3.0 |
| den_med_nec_behavioral | Clinical: Medical Necessity (Behavioral Health) | Clinical Documentation Improvement | CARC 50 | 0.4 | 0.8 | 3.5 |
| den_investigational | Clinical: Coverage Policy | Utilization Management | CARC 55, 57 | 0.35 | 0.6 | 4.0 |
| den_administrative | Mid-Cycle: Coding & Claim Submission | HIM / Coding | CARC 16, 4, 11 | 0.8 | 0.7 | 0.75 |
| den_service_excluded | Benefit Design: Contractual Exclusion | Contracting / Benefits | CARC 96, 204 | 0.25 | 0.15 | 2.0 |
| den_benefit_limit | Benefit Design: Benefit Maximum Reached | Contracting / Benefits | CARC 119, 35 | 0.3 | 0.2 | 1.0 |
| den_other | Unclassified | Revenue Integrity | n/a | 0.4 | 0.4 | 2.0 |

`Preventability`, `Appealability`, and `Effort (hrs)` are **assumptions** carrying RCM
domain judgement, not observed values. All three are adjustable and flow into the
sensitivity analysis.

---

## 7. Model assumptions

Everything not in this table is observed from source data.

| assumption | base | low | high | source |
|---|---|---|---|---|
| avg_allowed_amount_per_claim | 1336.32 | 1002.24 | 1737.21 | Derived in src/derive_claim_value.py from CMS DY2024 Inpatient (DRG), Outpatient (C-APC), and Physician payment files, weighted by a four-bucket claim mix and adjusted to commercial rates. Loaded live from outputs/claim_value.json. |
| appeal_cost_per_hour | 62.0 | 45.0 | 90.0 | Blended fully-loaded hourly rate for a denials analyst plus prorated clinical reviewer time. |
| collection_rate_on_overturn | 0.94 | 0.85 | 0.99 | Share of overturned claim value actually collected after secondary adjustments and patient responsibility. |
| resubmission_success_rate | 0.55 | 0.4 | 0.7 | Share of resubmitted (reworked) claims that ultimately pay. TC-PUF reports resubmission volume but not resubmission outcome, so this is the one funnel stage that is assumed rather than observed. |
| rework_touch_cost | 25.0 | 12.0 | 45.0 | Fully-loaded cost of one manual touch to rework and resubmit a denied claim, excluding formal appeal handling. |
| denial_value_at_risk_share | 0.25 | 0.15 | 0.4 | Share of a denied claim's allowed amount genuinely at risk. A claim-level denial event in TC-PUF is not a total loss: many are line-level, partial, duplicate, coordination-of-benefits routing, or zero-dollar administrative denials. Calibrated so modelled denial loss falls inside the published 3-5 percent of net patient revenue band. See CALIBRATION in docs/EXEC_MEMO.md. |

### Reference provider

420-bed non-profit acute care system with an employed physician group, operating in a single state. · 184,000 annual
marketplace claims. All findings are expressed as rates and rescale linearly to any
claim volume, verified by test case TC-030.

---

## 8. Row reconciliation

Source workbook through to harmonized panel.

| plan_year | schema_generation | source_rows | rows_after_footer_drop | unmapped_source_columns |
|---|---|---|---|---|
| 2022 | GEN1 | 5152 | 5152 | 5 |
| 2023 | GEN1 | 6764 | 6764 | 7 |
| 2024 | GEN2 | 5050 | 5050 | 5 |
| 2025 | GEN3 | 4541 | 4541 | 4 |
| 2026 | GEN3 | 4159 | 4159 | 4 |

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
