> ### ⚠️ This is a portfolio exercise, not a real engagement
>
> There is no client, no sponsor, and no approval. **The organization, the roles, the
> approval table, and the discovery interviews below are all constructed** — written in
> the standard form of a real BRD to demonstrate the artifact, not to record actual
> events. No real company, employer, or individual is described, and nothing here is a
> record of work performed for anyone.
>
> The **data and analysis are real**: public CMS files, reproducible via
> `python run_pipeline.py`. The stakeholder narrative around them is not.
>
> Author: Pratik Daga · portfolio project · see [`../README.md`](../README.md).

# Business Requirements Document
## Claims Denial Analytics & Recovery Program

| | |
|---|---|
| **Document ID** | BRD-RCM-DEN-001 |
| **Version** | 1.2 |
| **Status** | Approved for build |
| **Author** | Pratik Daga, Business Analyst |
| **Business Sponsor** | VP, Revenue Cycle |
| **Solution Owner** | Director, Revenue Integrity |
| **Last updated** | 2026-08-07 |

---

## 1. Document control

| Version | Date | Author | Change |
|---|---|---|---|
| 1.0 | 2026-07-14 | P. Daga | Initial draft after discovery interviews |
| 1.1 | 2026-07-28 | P. Daga | Added BRD-014/015 after Finance challenged the value model; added the reason-taxonomy constraint (BRD-021) |
| 1.2 | 2026-08-07 | P. Daga | Added BRD-024 calibration gate after Finance requested an external anchor for the dollar figure |

### Approvals

| Role | Name | Decision | Date |
|---|---|---|---|
| VP, Revenue Cycle | *(sponsor)* | Approved | 2026-08-01 |
| Director, Revenue Integrity | *(solution owner)* | Approved | 2026-08-01 |
| Director, Patient Access | *(impacted)* | Approved with comment — see §8 open item OI-02 | 2026-08-04 |
| Manager, HIM/Coding | *(impacted)* | Approved | 2026-08-01 |
| Director, Financial Planning | *(reviewer)* | Approved conditional on BRD-024 | 2026-08-06 |

---

## 2. Executive summary

The organization writes off a material share of net patient revenue to claim denials
and has no analytical basis for deciding which denials to prevent, which to appeal,
and which to accept. Denial management today is reactive: work queues are ordered by
claim age rather than by recoverable value, and no owner is accountable for denial
root cause upstream of billing.

This document specifies the requirements for a denial analytics capability that
quantifies denial volume and value by root cause, benchmarks payer denial behavior,
and produces a prioritized, owner-assigned action list.

**Scope boundary.** This release delivers the analytical capability and the
recommendation. It does not deliver workflow automation, payer contract renegotiation,
or changes to the clearinghouse. Those are candidate follow-on phases.

---

## 3. Business context and problem statement

### 3.1 Current state

Discovery interviews were conducted with Patient Access, HIM/Coding, Revenue Integrity,
Patient Financial Services, and Financial Planning. Findings:

- **No denial taxonomy.** Denials are worked from a flat work queue. There is no
  agreed mapping from payer denial reason to the internal process that caused it, so
  no department owns prevention.
- **Age-ordered, not value-ordered.** Work queues sort by days since denial. A $60
  administrative denial and a $40,000 inpatient medical necessity denial receive the
  same priority.
- **Appeal decisions are individual judgement.** Whether to appeal is decided per claim
  by the assigned analyst with no standard threshold, and appeal outcomes are not fed
  back into that decision.
- **No payer benchmark.** The organization cannot state whether a given payer denies
  more than its peers, so denial performance is never raised in payer negotiations.
- **No accepted dollar figure.** Finance and Revenue Cycle have quoted different
  denial-loss estimates in the same meeting, which has stalled investment decisions.

### 3.2 Problem statement

> The organization cannot quantify how much revenue it loses to claim denials, cannot
> attribute those losses to an accountable process owner, and therefore cannot decide
> where to invest in prevention versus recovery. In the absence of that analysis,
> denial work is prioritized by claim age, which systematically directs effort away
> from the highest-value recoverable denials.

### 3.3 Opportunity

Analysis of five plan years of CMS Transparency in Coverage data covering 277 issuers
and 1.88 billion commercial Exchange claims establishes the industry baseline:

| Observed measure | Value |
|---|---|
| Claims denied | 19.1% of claims received |
| Denials resubmitted (reworked) | 33.5% of denials, 2022–24 only \* |
| Denials formally appealed | 0.25% of denials |
| Appeals overturned in the member's favour | 39.7% of appeals filed |
| Denials never appealed | 99.75% |

\* Every other row pools all five experience years. Resubmission cannot: CMS did not
collect it before the PY2024 file, so 2020–21 are blank. In 2024 alone the rate was 34.7%.

The gap between how rarely denials are challenged and how often challenges succeed is
the central opportunity. See `docs/EXEC_MEMO.md` for the quantified recommendation.

> **Rate basis.** These are pooled 2020–24 industry rates. The dollar model in
> `EXEC_MEMO.md` is driven by 2024 rates only (denial 20.4%, overturn 32.6%). The two
> bases are not interchangeable; see the memo's "Which rates the dollar model uses".

---

## 4. Objectives and success measures

| ID | Objective | Success measure | Baseline | Target | Horizon |
|---|---|---|---|---|---|
| OBJ-01 | Quantify denial loss with a figure Finance and Revenue Cycle both accept | Single published figure cited by both functions | None | 1 agreed figure | 90 days |
| OBJ-02 | Attribute every denial to an accountable process owner | % of denials mapped to a named owner | 0% | ≥ 95% | 90 days |
| OBJ-03 | Replace age-ordered work queues with value-ordered | % of denial work driven by priority score | 0% | ≥ 80% | 180 days |
| OBJ-04 | Raise appeal rate on positive-ROI denial categories | Appeal rate, positive-ROI categories only | 0.26% | ≥ 5% | 180 days |
| OBJ-05 | Reduce preventable denial volume | Denial rate on front-end categories | Baseline yr 1 | −20% | 12 months |
| OBJ-06 | Establish payer denial benchmarking in contract negotiation | Payer reviews using denial scorecard | 0 | All major payers | 12 months |

---

## 5. Scope

### 5.1 In scope

- Acquisition and harmonization of CMS Transparency in Coverage PUF, plan years 2022–2026
- Derivation of claim value from CMS Medicare payment files
- Denial root-cause taxonomy mapping payer reason codes to internal process owners
- Recovery and prevention value model with declared assumptions and sensitivity analysis
- Payer benchmark scorecard
- Interactive dashboard and a Power BI dimensional model
- Prioritized action list assigned to named owners

### 5.2 Out of scope

| Item | Rationale |
|---|---|
| Workflow automation of appeal submission | Requires clearinghouse integration; candidate Phase 2 |
| Payer contract renegotiation | Consumes this analysis but is a separate commercial workstream |
| Patient-level or PHI-bearing analysis | No PHI is used; the analysis is built entirely on public aggregate data |
| Medicare, Medicaid, or self-pay denials | Source data covers commercial Exchange plans only |
| Real-time or near-real-time refresh | Source is published annually |

### 5.3 Assumptions

| ID | Assumption | Risk if false |
|---|---|---|
| ASM-01 | Payer-reported Exchange denial behavior is representative of the organization's commercial payer mix | Rates would need recalibration against internal 835 remittance data |
| ASM-02 | CMS continues annual TC-PUF publication | Trend analysis stops; point-in-time analysis remains valid |
| ASM-03 | Internal 835 remittance data can be obtained in Phase 2 to replace modelled reason mix with observed | Reason mix remains limited by the 60% "Other" reporting problem |

### 5.4 Constraints

| ID | Constraint |
|---|---|
| CON-01 | Source data is payer self-reported and unaudited |
| CON-02 | Source reports claim **counts**, not dollars; monetization requires a derived claim value |
| CON-03 | Source covers federally-facilitated Exchange states only (33 states); state-based Exchanges do not report to this file |
| CON-04 | Data has a two-year lag: the PY2026 file carries CY2024 experience |

---

## 6. Functional requirements

Priority uses MoSCoW. Every requirement is traceable to a test case in
`docs/RTM.csv` and a script in `docs/UAT_TEST_SCRIPTS.md`.

### 6.1 Data acquisition and harmonization

| ID | Requirement | Priority | Acceptance criteria |
|---|---|---|---|
| BRD-001 | The system shall ingest CMS Transparency in Coverage PUF for plan years 2022 through 2026 | Must | All five workbooks ingested; row counts reconcile to source in `outputs/reconciliation.csv` |
| BRD-002 | The system shall harmonize three source schema generations into one canonical panel | Must | Every source column is either mapped or listed as unmapped in the reconciliation output; no column is silently dropped |
| BRD-003 | The system shall preserve CMS suppression markers as distinguishable states rather than coercing them to zero | Must | Each measure has a companion `_flag` column recording `not_available`, `suppressed_small_cell`, `not_required`, or `not_applicable`; suppressed values are NULL, never 0 |
| BRD-004 | The system shall deduplicate issuer-level measures to issuer grain before aggregation | Must | Issuer totals computed at issuer grain; DQ log quantifies the overstatement a naive sum would produce |
| BRD-005 | The system shall suppress computed rates below a minimum denominator | Should | Denial rates require ≥ 100 claims received; overturn rates require ≥ 10 appeals filed |
| BRD-006 | The system shall reject rates exceeding 100% | Must | Any rate > 1.0 is set NULL and logged with severity High |
| BRD-007 | The system shall produce a data quality log with severity, finding, treatment, and rows affected | Must | `outputs/dq_log.csv` exists with all four attributes populated for every finding |

### 6.2 Denial root-cause attribution

| ID | Requirement | Priority | Acceptance criteria |
|---|---|---|---|
| BRD-010 | The system shall map each payer denial reason category to an RCM root cause | Must | All 10 source categories mapped; no category unmapped |
| BRD-011 | The system shall assign each root cause to a named accountable owner | Must | Every root cause carries an owner from the agreed org list |
| BRD-012 | The system shall record representative X12 CARC codes for each root cause | Should | CARC examples present for all categories except `Unclassified` |
| BRD-013 | The system shall compute denial reason mix only from plan-years whose categories reconcile to reported total denials | Must | Reason mix excludes non-reconciling rows; reconciliation rate is reported |
| BRD-014 | The system shall express preventability per root cause as an explicit, adjustable parameter | Must | Preventability declared per category in config and adjustable in the dashboard |
| BRD-015 | The system shall express appeal effort per root cause as an explicit, adjustable parameter | Must | Effort hours declared per category and flow into appeal cost |

### 6.3 Value model

| ID | Requirement | Priority | Acceptance criteria |
|---|---|---|---|
| BRD-016 | The system shall derive average allowed amount per claim from published payment data rather than assert it | Must | Derivation reads CMS DY2024 inpatient, outpatient, and physician files; every step is logged to `outputs/claim_value_derivation.csv` |
| BRD-017 | The system shall separate observed inputs from assumed inputs in all reporting | Must | Dashboard Method tab classifies every input as Observed, Derived, or Assumed |
| BRD-018 | The system shall compute recovery value net of the cost to obtain it | Must | Net recovery = gross recovery − appeal cost; ROI reported per category |
| BRD-019 | The system shall recommend appeal only for categories where ROI exceeds 1.0 | Must | `appeal_recommended` flag set per category; selective and blanket totals both reported |
| BRD-020 | The system shall value denial prevention separately from denial recovery | Must | Prevention value and net recovery reported as distinct measures |
| BRD-022 | The system shall perform one-at-a-time sensitivity analysis across every assumption | Must | `outputs/sensitivity.csv` covers all assumptions at declared low and high bounds |
| BRD-023 | The system shall expose every assumption as a user-adjustable control | Should | Each assumption is a dashboard slider bounded by its declared range |
| BRD-024 | The system shall validate modelled denial loss against a published external benchmark and fail visibly when outside it | Must | Calibration check compares modelled loss to the 3–5% of net patient revenue band; status is displayed and written to `outputs/calibration_check.csv` |

### 6.4 Reporting and benchmarking

| ID | Requirement | Priority | Acceptance criteria |
|---|---|---|---|
| BRD-025 | The system shall benchmark each payer against peer medians on denial, appeal, and overturn rate | Must | Percentile rank computed per payer for all three measures |
| BRD-026 | The system shall identify priority appeal targets as payers that both deny and overturn above median | Should | Composite target score computed and rendered |
| BRD-027 | The system shall report denial rate by state | Should | State view present with issuer counts |
| BRD-028 | The system shall produce a prioritized action list assigning each root cause a rank, wave, and owner | Must | `outputs/prioritization.csv` contains rank, wave, owner, and value for every root cause |
| BRD-029 | The system shall deliver a Power BI ready dimensional model | Must | Star schema exported with conformed dimensions, a Type 2 payer dimension, and DAX measure definitions; referential integrity passes |
| BRD-030 | The system shall allow the reader to rescale all findings to any provider claim volume | Should | Claim volume is a dashboard input; all outputs recompute |

### 6.5 Constraint disclosure

| ID | Requirement | Priority | Acceptance criteria |
|---|---|---|---|
| BRD-021 | The system shall disclose the share of denials reported as unclassified and flag the limit this places on root-cause management | Must | Unclassified share displayed prominently with the associated recommendation |
| BRD-031 | The system shall document data provenance including source, vintage, and known scope limitations | Must | Provenance section names each source file, row count, and scope caveat |

---

## 7. Non-functional requirements

| ID | Requirement | Acceptance criteria |
|---|---|---|
| NFR-01 | The full pipeline shall run end to end from a single command | `python run_pipeline.py` completes with exit code 0 |
| NFR-02 | The pipeline shall complete within 5 minutes excluding downloads | Measured runtime under 300s |
| NFR-03 | The pipeline shall be reproducible from raw source without manual steps | Fresh clone plus download produces identical outputs |
| NFR-04 | The dashboard shall respond to an assumption change within 3 seconds | Observed re-render under 3s |
| NFR-05 | No protected health information shall be used or stored | All sources are public aggregate files; documented in provenance |
| NFR-06 | Every published figure shall be traceable to a source file and transformation | Each output CSV names its inputs in the generating module docstring |

---

## 8. Open items

| ID | Item | Owner | Status |
|---|---|---|---|
| OI-01 | Obtain internal 835 remittance extract to replace modelled reason mix with observed CARC detail | Revenue Integrity | Open — Phase 2 |
| OI-02 | Patient Access noted that eligibility verification is partly performed by a vendor; preventability for front-end categories may be constrained by the vendor SLA | Director, Patient Access | Open — requires contract review |
| OI-03 | Confirm whether the organization's payer mix skews toward issuers in the high-denial cohort | Managed Care Contracting | Open |
| OI-04 | Validate the 55% resubmission success assumption against internal rework outcomes | Patient Financial Services | Open — the only funnel stage not observed |

---

## 9. Related documents

- `docs/PROCESS_MAPS.md` — as-is and to-be claims-to-cash process
- `docs/RTM.csv` — requirements traceability matrix
- `docs/UAT_TEST_SCRIPTS.md` — user acceptance test scripts
- `docs/UAT_DEFECT_LOG.csv` — defects raised during UAT
- `docs/DATA_DICTIONARY.md` — canonical schema and source-to-target mapping
- `docs/EXEC_MEMO.md` — executive recommendation
