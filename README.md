# Healthcare Revenue Cycle: Claims Denial Analytics & Recovery Model

Quantifies where commercial claim denials originate, what recovering and preventing
them is worth, and which department owns the fix — built on five plan years of CMS
Transparency in Coverage data covering **277 issuers and 1.88 billion claims**.

**Live dashboard:** https://pratikxx-rcm-denial-analytics-app-nxqr62.streamlit.app/
**Source:** https://github.com/PratiKxx/rcm-denial-analytics

---

## The finding

| | |
|---|---|
| Claims denied | **19.1%** of claims received |
| Denials formally appealed | **0.25%** |
| Appeals overturned | **39.7%** |
| Denials never appealed | **99.75%** |

Almost nobody appeals, and appeals usually work. That looks like an obvious pot of
money — and the analysis concludes it mostly is not.

Once the labour cost of an appeal is netted against its expected recovery, only **5 of
10** denial categories return more than they consume. Blanket appealing nets $22K at
the reference provider's volume; appealing only the positive-ROI categories nets
$288K. **Prevention is worth 18x more than recovery.**

The recommendation is the opposite of the intuition, which is the point of doing the
analysis rather than acting on the headline.

Full argument: [`docs/EXEC_MEMO.md`](docs/EXEC_MEMO.md)

---

## What is observed vs assumed

The credibility of every dollar figure rests on this separation, and the model enforces it.

- **Observed** (not adjustable): denial rate, resubmission rate, appeal rate, overturn
  rate, denial reason mix — all reported to CMS by 277 issuers.
- **Derived** from published CMS payment data: average allowed amount per claim
  ($1,336, built from 1.51M rows across three CMS payment files, allocated over four
  claim-mix buckets).
- **Assumed** with declared bounds: six parameters, every one exposed as a dashboard
  slider and stress-tested in `outputs/sensitivity.csv`.

> **Rate basis.** The 19.1% / 0.25% / 39.7% figures above are the **pooled 2020–24**
> industry baseline. The dollar model is driven by **2024 rates only** (denial 20.4%,
> overturn 32.6%) because a forward-looking recovery model should reflect current payer
> behaviour rather than a series containing COVID-distorted 2020–21. The 2024 overturn
> rate is the more conservative of the two. Reproducing the model from the pooled rates
> will not give $5.35M.

### Calibration gate

A dollar model defended only by its own inputs is not defensible. Modelled denial loss
is checked against the published **3–5% of net patient revenue** industry band on every
run. Current: **4.12% — PASS**. Move the assumptions far enough and the dashboard
displays a calibration failure instead of a bigger number.

---

## Business analysis artifacts

The analysis is half the deliverable. These are the other half.

| Document | What it is |
|---|---|
| [`docs/BRD.md`](docs/BRD.md) | Business requirements — 35 numbered, testable requirements with acceptance criteria, MoSCoW priority, approvals, open items |
| [`docs/PROCESS_MAPS.md`](docs/PROCESS_MAPS.md) | As-is and to-be claims-to-cash process, swimlane, RACI, and denial origination mapping |
| [`docs/RTM.csv`](docs/RTM.csv) | Requirements traceability matrix — **generated**, so it cannot drift from the build |
| [`docs/UAT_TEST_SCRIPTS.md`](docs/UAT_TEST_SCRIPTS.md) | 23 acceptance test scripts, **executable** via `tests/test_uat.py` |
| [`docs/UAT_DEFECT_LOG.csv`](docs/UAT_DEFECT_LOG.csv) | 8 defects raised during build and UAT, with root cause and resolution |
| [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md) | Canonical schema and source-to-target mapping — **generated** from the live config |
| [`docs/EXEC_MEMO.md`](docs/EXEC_MEMO.md) | Two-page recommendation with a defended dollar figure |

> The BRD and executive memo are **portfolio constructs** — the organization,
> stakeholders, and approvals in them are written to demonstrate the artifact, not to
> record a real engagement. Each carries a disclaimer at the top. The data and analysis
> underneath are real and reproducible.

---

## Data engineering

Five plan years arrive in **three incompatible schema generations** and need real work
before they are analyzable.

- **Schema harmonization.** PY2022–23 report claim totals with no network split;
  PY2024 introduces the split and ships one header with a stray trailing double quote;
  PY2025–26 rename the enrollment fields. All three map to one canonical model with an
  explicit source-to-target mapping.
- **Suppression handling.** CMS uses `*`, `**`, `***`, and `N/A` instead of nulls.
  Reading them as zero inflates every rate downstream. Each is preserved as a distinct
  state in a companion `_flag` column.
- **Denormalization trap.** Issuer-level measures repeat across every plan row. Summing
  at plan grain overstates national volume **84x** — and produces a plausible-looking
  number rather than an obvious error. Deduplicated to issuer grain before aggregation.
- **Reconciliation.** Only 18% of plan-years (4,640 of 25,666) have denial reason
  categories that sum to reported totals. Most of the shortfall is plan-years reporting
  no reason detail at all; of the 11,000 that report both a total and some reason
  detail, 6,250 still fail to reconcile. Verified the mapping is correct by testing
  against every candidate denominator, then disclosed the gap rather than smoothing it.

112 data quality findings logged with severity, treatment, and rows affected in
`outputs/dq_log.csv`.

---

## Dimensional model

`data/processed/star/` — Kimball star schema ready for Power BI import.

- 5 dimensions, 2 facts, referential integrity verified in test
- `dim_payer` is **Type 2 SCD** — issuer names change across plan years while IDs
  persist, so denial history stays attached to the name in force at the time
  (6 name changes tracked)
- `measures.dax` carries DAX measure definitions and the relationship list

---

## Running it

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
python run_pipeline.py
python tests/test_uat.py
streamlit run app.py
```

`run_pipeline.py --skip-download` reuses files already in `data/raw`.
Full pipeline runs in ~17s excluding downloads.

### Pipeline

| Stage | Module | Output |
|---|---|---|
| 1 | `src/download_tcpuf.py` | 5 TC-PUF workbooks |
| 2 | `src/download_cms_payments.py` | 3 CMS payment files (575 MB) |
| 3 | `src/harmonize.py` | Canonical panels + DQ log + reconciliation |
| 4 | `src/derive_claim_value.py` | Claim value derivation |
| 5 | `src/analyze.py` | Funnel, root cause, recovery model, prioritization, sensitivity |
| 6 | `src/star_schema.py` | Power BI star schema + DAX |

Docs regenerate via `src/generate_rtm.py` and `src/generate_data_dictionary.py`.

---

## Data sources

All public. **No protected health information is used at any stage.**

| Source | Publisher | Vintage |
|---|---|---|
| Transparency in Coverage PUF | CMS / CCIIO | PY2022–PY2026 |
| Medicare Inpatient Hospitals by Provider and Service | CMS | DY2024 |
| Medicare Outpatient Hospitals by Provider and Service | CMS | DY2024 |
| Medicare Physician & Other Practitioners by Provider | CMS | DY2024 |

**Known limitations**, disclosed rather than buried: TC-PUF is payer self-reported and
unaudited, covers federally-facilitated Exchange plans in 33 states only, reports claim
counts rather than dollars, and carries a two-year lag. The CMS outpatient file covers
Comprehensive APCs only — catching that prevented a tenfold overstatement of claim
value (defect DEF-001).
