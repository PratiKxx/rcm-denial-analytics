# Healthcare Revenue Cycle: Claims Denial Analytics & Recovery Model

I analyzed five plan years of CMS Transparency in Coverage data — **277 health insurers
and 1.88 billion commercial claims** — to work out where claim denials originate, what
recovering and preventing them is actually worth, and which department owns the fix.

**Live dashboard:** https://claims-denial-analytics.streamlit.app/
**Source:** https://github.com/PratiKxx/rcm-denial-analytics

---

## What I found

| | |
|---|---|
| Claims denied | **19.1%** of claims received |
| Denials formally appealed | **0.25%** |
| Appeals overturned | **39.7%** |
| Denials never appealed | **99.75%** |

Almost nobody appeals, and appeals usually work. That reads like an obvious pot of
money, and my first instinct was to size it and recommend appealing harder.

That turned out to be wrong. Once I netted the labour cost of an appeal against its
expected recovery, only **5 of 10** denial categories return more than they consume.
Appealing everything nets $22K at the reference provider's volume; appealing only the
positive-ROI categories nets $288K — 13x more, from the same denial pool, by working
*less* of it. And **prevention is worth 18x more than recovery**, because a prevented
denial never incurs rework cost and never enters the write-off pool.

So the recommendation I ended up making is the opposite of the one the headline
suggests. That gap is the reason to do the analysis instead of acting on the intuition.

Full argument: [`docs/EXEC_MEMO.md`](docs/EXEC_MEMO.md)

---

## Observed vs assumed

Every dollar figure here depends on this separation, so I enforced it in the model
rather than just claiming it.

- **Observed** (not adjustable): denial rate, resubmission rate, appeal rate, overturn
  rate, denial reason mix. These are what 277 issuers reported to CMS — I did not model
  them.
- **Derived** from published CMS payment data: average allowed amount per claim,
  $1,336, built from 1.51M rows across three CMS payment files and allocated over four
  claim-mix buckets.
- **Assumed**, with declared bounds: six parameters. Each one is a slider in the
  dashboard and each is stress-tested in `outputs/sensitivity.csv`.

> **Rate basis.** The 19.1% / 0.25% / 39.7% figures above are the **pooled 2020–24**
> industry baseline. I drive the dollar model off **2024 rates only** (denial 20.4%,
> overturn 32.6%), because a forward-looking recovery model should reflect current payer
> behaviour rather than a series containing COVID-distorted 2020–21. The 2024 overturn
> rate is the more conservative of the two. Reproducing the model from the pooled rates
> will not give $5.35M.

### Calibration gate

A dollar model that can only ever agree with its own inputs isn't defensible. So I
anchored this one externally: modelled denial loss is checked against the published
**3–5% of net patient revenue** industry band on every run. It currently sits at
**4.12% — PASS**. Push the assumptions far enough and the dashboard reports a
calibration *failure* rather than a bigger number. The model can be wrong, but it
can't be wrong quietly.

---

## Business analysis artifacts

The analysis is half the deliverable. This is the other half.

| Document | What it is |
|---|---|
| [`docs/BRD.md`](docs/BRD.md) | Business requirements — 35 numbered, testable requirements with acceptance criteria, MoSCoW priority, approvals, open items |
| [`docs/PROCESS_MAPS.md`](docs/PROCESS_MAPS.md) | As-is and to-be claims-to-cash process, swimlane, RACI, and denial origination mapping |
| [`docs/RTM.csv`](docs/RTM.csv) | Requirements traceability matrix — **generated**, so it can't drift from the build |
| [`docs/UAT_TEST_SCRIPTS.md`](docs/UAT_TEST_SCRIPTS.md) | 23 acceptance test scripts, **executable** via `tests/test_uat.py` |
| [`docs/UAT_DEFECT_LOG.csv`](docs/UAT_DEFECT_LOG.csv) | 8 defects I hit during build and UAT, with root cause and resolution |
| [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md) | Canonical schema and source-to-target mapping — **generated** from the live config |
| [`docs/EXEC_MEMO.md`](docs/EXEC_MEMO.md) | Two-page recommendation with a defended dollar figure |

Two of these are generated rather than hand-written, which was deliberate: a
traceability matrix and a data dictionary maintained by hand are both wrong the first
time someone renames a column.

> The BRD and executive memo are **portfolio constructs**. The organization,
> stakeholders, and approvals in them are written to demonstrate the artifact, not to
> record a real engagement — each carries a disclaimer saying so at the top. The data
> and analysis underneath are real and reproducible.

---

## Data engineering

The five plan years arrive in **three incompatible schema generations**, and most of the
work was getting them into a state where they could be analyzed at all.

- **Schema harmonization.** PY2022–23 report claim totals with no network split; PY2024
  introduces the split and ships one header with a stray trailing double quote; PY2025–26
  rename the enrollment fields. I mapped all three to one canonical model with an
  explicit source-to-target mapping.
- **Suppression handling.** CMS uses `*`, `**`, `***`, and `N/A` instead of nulls.
  Reading those as zero inflates every rate computed downstream, so I preserved each as
  a distinct state in a companion `_flag` column.
- **Denormalization trap.** Issuer-level measures repeat across every plan row. Summing
  at plan grain overstates national volume **84x** — and it produces a plausible-looking
  number rather than an obvious error, which is what makes it dangerous. Deduplicated to
  issuer grain before any aggregation.
- **Reconciliation.** Only 18% of plan-years (4,640 of 25,666) have denial reason
  categories that sum to reported totals. Most of the shortfall is plan-years reporting
  no reason detail at all; of the ~11,000 that report both a total and some detail, 6,250
  still fail to reconcile. I confirmed my mapping was correct by testing the reason sum
  against every candidate denominator, then disclosed the gap instead of smoothing it.

112 data quality findings are logged with severity, treatment, and rows affected in
`outputs/dq_log.csv`.

---

## Dimensional model

`data/processed/star/` — a Kimball star schema ready for Power BI import.

- 5 dimensions, 2 facts, referential integrity verified in test
- `dim_payer` is a **Type 2 SCD**. Issuer names change across plan years while the IDs
  persist, so overwriting the name would silently re-attribute a 2021 denial to a 2024
  name. Type 2 keeps each denial attached to the name in force at the time (6 changes
  tracked).
- `measures.dax` carries the DAX measure definitions and the relationship list

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

`run_pipeline.py --skip-download` reuses files already in `data/raw`. The full pipeline
runs in about 17 seconds excluding downloads.

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

**Known limitations**, which I'd rather state than bury: TC-PUF is payer self-reported
and unaudited, covers federally-facilitated Exchange plans in 33 states only, reports
claim counts rather than dollars, and carries a two-year lag.

The CMS outpatient file is the one that nearly caught me out — it covers Comprehensive
APCs only, 72 procedural groups averaging $5,123 per service, with routine lab, imaging,
and clinic volume absent entirely. Treating that as the outpatient average overstated my
blended claim value roughly tenfold. I only found it by checking which APC codes were
actually present in the file (defect DEF-001).
