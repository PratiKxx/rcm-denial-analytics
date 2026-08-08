# User Acceptance Test Scripts

Document ID: UAT-RCM-DEN-001 · Companion to `BRD.md` and `RTM.csv`

---

## 1. Approach

Test cases are **executable**, not narrative. `tests/test_uat.py` implements every
script below and writes results to `docs/UAT_RESULTS.csv`. Any failure generates a
row in `docs/UAT_DEFECT_LOG.csv` with the assertion message as the defect detail.

This matters for a data product specifically. A narrative script that says "verify the
denial rate looks reasonable" passes whatever the analyst wants it to pass. An
assertion that says no rate may exceed 1.0 either holds or it does not, and it re-runs
on every build.

**Run:**

```bash
python tests/test_uat.py
```

Exit code 0 means all cases passed. Non-zero means at least one defect was written.

### Entry criteria

- `python run_pipeline.py` completes with exit code 0
- All outputs present in `outputs/` and `data/processed/`

### Exit criteria

- 100% of Must-priority requirements pass
- No open Critical or High defect
- Every requirement in `RTM.csv` shows a test case or an explicit inspection basis

### Current status

| Metric | Value |
|---|---|
| Test cases executed | 23 |
| Passed | 23 |
| Failed | 0 |
| Requirements covered by automated test | 28 of 35 |
| Requirements verified by inspection | 7 (BRD-023 and the six NFRs) |
| Defects raised during build and UAT | 8 |
| Defects open | 0 |
| Defects closed Won't Fix | 1 (DEF-006, documented source-data constraint) |

---

## 2. Test scripts

### TC-001 — All five plan years ingested
**Requirement:** BRD-001
**Precondition:** `data/raw/tcpuf/` contains five workbooks
**Steps**
1. Run the harmonization stage.
2. Open `outputs/reconciliation.csv`.
3. Confirm one row per plan year 2022–2026.
4. Confirm every row reports non-zero source rows.

**Expected:** Five plan years present, all with non-zero source row counts.
**Actual:** 5 plan years, 25,666 source rows. **PASS**

---

### TC-002 — Schema generations harmonized without silent column loss
**Requirement:** BRD-002
**Steps**
1. Confirm the reconciliation output records three distinct schema generations.
2. Confirm any source column not mapped to the canonical model is listed explicitly.

**Expected:** Three generations; unmapped columns disclosed rather than dropped silently.
**Actual:** 3 generations; 25 source columns explicitly listed as unmapped. **PASS**

> Defect DEF-005 was raised here: PY2024 ships a header with a trailing double quote,
> which caused the out-of-network denial column to be dropped without error.

---

### TC-003 — Suppression markers are not coerced to zero
**Requirement:** BRD-003
**Steps**
1. For each measure with a companion `_flag` column, select rows where the flag is set.
2. Confirm the measure is NULL for every such row.
3. Confirm no suppressed cell carries a numeric value, particularly zero.

**Expected:** Suppressed cells NULL, never 0.
**Actual:** 32 flag columns; 17,347 rows carry at least one suppression marker; 0 coerced to zero. **PASS**

> Why this matters: CMS uses `*`, `**`, `***`, and `N/A` where a value is withheld.
> Reading those as zero inflates every rate computed from the affected denominator.

---

### TC-004 — Issuer measures deduplicated to issuer grain
**Requirement:** BRD-004
**Steps**
1. Confirm the issuer panel has exactly one row per issuer per plan year.
2. Compute the total a naive plan-grain sum would produce.
3. Confirm the overstatement is material and quantified in the DQ log.

**Expected:** No duplicate issuer-years; overstatement quantified.
**Actual:** 1,043 issuer-years, 0 duplicates; a naive plan-grain sum would overstate volume 84.1x. **PASS**

> Defect DEF-004. This is the failure mode most likely to survive into a finished
> deliverable, because 157 billion claims looks like a big number rather than a wrong one.

---

### TC-005 — Rates suppressed below minimum denominator
**Requirement:** BRD-005
**Steps**
1. Confirm no denial rate exists where claims received is below 100.
2. Confirm no overturn rate exists where appeals filed is below 10.

**Expected:** Denominator floors enforced.
**Actual:** Both floors enforced. **PASS**

---

### TC-006 — No rate exceeds 100 percent
**Requirement:** BRD-006
**Steps**
1. For all seven computed rate fields, confirm every value is within [0, 1] or NULL.

**Expected:** No rate above 1.0, no negative rate.
**Actual:** 7 rate fields validated. **PASS**

---

### TC-007 — Data quality log is complete
**Requirement:** BRD-007
**Steps**
1. Confirm `outputs/dq_log.csv` exists.
2. Confirm every finding carries id, severity, field, finding, treatment, rows affected.
3. Confirm at least one Critical finding is recorded.

**Expected:** All attributes populated; Critical findings present.
**Actual:** 112 findings across 7 IDs; 2 Critical, 3 High. **PASS**

---

### TC-010 — Every denial reason mapped to root cause and owner
**Requirement:** BRD-010, BRD-011, BRD-012
**Steps**
1. Confirm all 10 source denial categories appear in the taxonomy.
2. Confirm each carries a root cause, an accountable owner, CARC examples, and the three weighting parameters.

**Expected:** 10 of 10 mapped, no missing attributes.
**Actual:** 10/10 mapped across 6 accountable owners. **PASS**

---

### TC-013 — Reason mix uses only reconciling plan-years
**Requirement:** BRD-013
**Steps**
1. Compute the reason mix.
2. Confirm its basis equals the count of plan-years flagged as reconciling.
3. Confirm the basis is strictly less than the full panel.
4. Confirm shares sum to 1.0.

**Expected:** Mix restricted to reconciling rows; shares sum to 1.
**Actual:** Mix computed on 4,640 of 25,666 plan-years (18%); shares sum to 1.0. **PASS**

> Defect DEF-006, closed Won't Fix. Only 18% of plan-years reconcile. The mapping was
> verified correct by testing the reason sum against in-network, out-of-network,
> issuer-level, and combined denominators; total was the best match in all three schema
> generations. The inconsistency is in the source, so it is disclosed rather than smoothed.

---

### TC-014 — Preventability and effort are explicit adjustable parameters
**Requirement:** BRD-014, BRD-015
**Steps**
1. Confirm preventability and appealability are within [0, 1] for every category.
2. Confirm effort hours are positive and plausible.
3. Confirm preventability is not uniform across categories.

**Expected:** Valid ranges; genuine variation across categories.
**Actual:** 10 categories; preventability 25%–90%, effort 0.5–4.0h. **PASS**

---

### TC-016 — Claim value derived from published payment data
**Requirement:** BRD-016
**Steps**
1. Confirm the derivation reads CMS inpatient, outpatient, and physician files.
2. Confirm the blended value sits between its declared low and high bounds.
3. Confirm all four claim-mix buckets are present.

**Expected:** Value derived, not asserted; every step logged.
**Actual:** $1,336.32/claim from 1,506,136 distinct rows across 3 CMS files, allocated over 4 buckets. **PASS**

> Defects DEF-001 and DEF-002 were both raised against this test case.

---

### TC-017 — Observed inputs separated from assumed inputs
**Requirement:** BRD-017
**Steps**
1. Confirm every assumption declares value, low, high, and a source description.
2. Confirm each value sits within its own declared bounds.
3. Confirm no observed rate (denial, appeal, overturn, resubmission) is declared as an assumption.

**Expected:** Clean separation; no observed rate is adjustable.
**Actual:** 6 assumptions declared with bounds and sources; 0 observed rates among them. **PASS**

---

### TC-018 — Recovery is net of cost and appeal is selective
**Requirement:** BRD-018, BRD-019
**Steps**
1. Confirm net recovery equals gross recovery minus appeal cost for every category.
2. Confirm the appeal recommendation flag follows the ROI > 1.0 threshold exactly.
3. Confirm selective appeal outperforms blanket appeal.

**Expected:** Arithmetic holds; selective beats blanket.
**Actual:** 5/10 categories appeal-positive; selective $287,651 vs blanket $21,583. **PASS**

---

### TC-020 — Prevention value reported separately from recovery
**Requirement:** BRD-020
**Steps**
1. Confirm prevention and net recovery are distinct columns with distinct values.
2. Confirm total opportunity equals prevention plus selective recovery.

**Expected:** Distinct measures that reconcile to the total.
**Actual:** Prevention $5,063,865 vs recovery $287,651 (18x). **PASS**

---

### TC-021 — Unclassified denial share disclosed
**Requirement:** BRD-021
**Steps**
1. Confirm the unclassified share is computed and available for display.
2. Confirm it is material rather than negligible.

**Expected:** Share computed and surfaced.
**Actual:** Unclassified share 60.4% disclosed. **PASS**

---

### TC-022 — Sensitivity covers every assumption
**Requirement:** BRD-022
**Steps**
1. Confirm every declared assumption appears in the sensitivity output.
2. Confirm each is tested at both its low and high bound.

**Expected:** Full coverage at both bounds.
**Actual:** 6 assumptions x 2 bounds tested. **PASS**

---

### TC-024 — Calibration gate against external benchmark
**Requirement:** BRD-024
**Steps**
1. Compute modelled denial loss as a share of gross claim value.
2. Confirm it falls inside the published 3–5% of net patient revenue band.
3. Confirm the status is written to `outputs/calibration_check.csv`.

**Expected:** PASS status, loss inside the band.
**Actual:** Modelled loss 4.12% within 3%–5%. **PASS**

> Defect DEF-003. This test case exists because Finance declined to accept a dollar
> figure defended only by its own inputs. The gate anchors the model to an external
> reference and fails loudly rather than quietly drifting.

---

### TC-025 — Payer benchmark with peer percentiles
**Requirement:** BRD-025, BRD-026
**Steps**
1. Confirm percentile rank is computed for denial, appeal, and overturn rate.
2. Confirm all percentiles fall within [0, 1].
3. Confirm the composite appeal target score is present.

**Expected:** Three percentile measures plus composite score.
**Actual:** 152 payers benchmarked on 3 percentile measures. **PASS**

---

### TC-027 — State-level denial reporting
**Requirement:** BRD-027
**Steps**
1. Confirm the state summary carries state, issuer count, denial rate, claims received.
2. Confirm denial rates fall within [0, 1].

**Expected:** State view present and valid.
**Actual:** 30 states; denial rate 7.9%–32.0%. **PASS**

---

### TC-028 — Prioritized action list with owner and wave
**Requirement:** BRD-028
**Steps**
1. Confirm every root cause has rank, wave, owner, opportunity, and priority score.
2. Confirm ranks are ordered and priority score descends monotonically.

**Expected:** Complete, correctly ordered action list.
**Actual:** 9 root causes ranked across 3 waves. **PASS**

---

### TC-029 — Star schema with referential integrity
**Requirement:** BRD-029
**Steps**
1. Confirm all seven star schema tables and the DAX measure file exist.
2. Confirm every fact foreign key resolves to its dimension.
3. Confirm the payer dimension carries SCD Type 2 columns and exactly one current row per issuer.

**Expected:** No orphan keys; valid Type 2 dimension.
**Actual:** 7 tables, referential integrity PASS, 6 SCD2 name changes tracked. **PASS**

---

### TC-030 — Findings rescale to any provider claim volume
**Requirement:** BRD-030
**Steps**
1. Compute total opportunity at the base claim volume.
2. Recompute at double the volume.
3. Confirm the result scales linearly.

**Expected:** Linear scaling, confirming findings are rate-based.
**Actual:** 2x volume → 2.000x opportunity. **PASS**

---

### TC-031 — Provenance documented with source and scope caveats
**Requirement:** BRD-031
**Steps**
1. Confirm the derivation carries a note and per-bucket scope notes.
2. Confirm the C-APC scope limitation is recorded in the DQ log as DQ-010.
3. Confirm reconciliation covers all five plan years.

**Expected:** Scope limitations disclosed at source, not buried.
**Actual:** 3 buckets scope-noted; DQ-010 logged; 5 plan years reconciled. **PASS**

---

## 3. Requirements verified by inspection

| Requirement | Basis |
|---|---|
| BRD-023 | Visual confirmation that each assumption renders as a bounded slider in the dashboard sidebar |
| NFR-01 | `python run_pipeline.py` returns exit code 0 |
| NFR-02 | Measured pipeline runtime 16.8s excluding downloads, against a 300s ceiling |
| NFR-03 | Full pipeline re-run from raw source reproduces identical outputs |
| NFR-04 | Dashboard re-render observed under 3s on assumption change |
| NFR-05 | All sources are public aggregate files; no patient-level data is read at any stage |
| NFR-06 | Each module docstring names its inputs and outputs |
