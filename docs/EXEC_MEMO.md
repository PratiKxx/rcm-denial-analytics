> ### ⚠️ This is a portfolio exercise, not a real engagement
>
> **The recipients, the organization, and the requests for decision below are
> constructed** — written in the form of a real executive memo to demonstrate the
> artifact. No real company, employer, or individual is described, and no actual
> approval was sought or given.
>
> The **data and analysis are real**: public CMS files, reproducible via
> `python run_pipeline.py`. The reference provider is an illustrative scaling unit, not
> a client. The dollar figure is a modelled illustration with a declared range, not a
> measured result.
>
> Author: Pratik Daga · portfolio project · see [`../README.md`](../README.md).

# Memorandum

**To:** VP, Revenue Cycle · Director, Financial Planning
**From:** Pratik Daga, Business Analyst
**Date:** 7 August 2026
**Subject:** Denial recovery and prevention — where the money is, and where it is not
**Supporting analysis:** `docs/BRD.md`, dashboard, `outputs/`

---

## Recommendation

Invest in **denial prevention, not denial recovery**. Prevention is worth roughly
**18 times** more than appeals at our claim volume, and the intuitive move — appeal
more aggressively — destroys most of its own value when applied broadly.

Specifically:

1. **Fund front-end and coding prevention first.** $4.0M of the $5.4M annual
   opportunity sits in two root causes owned by HIM/Coding and Revenue Integrity.
2. **Appeal selectively, on five of ten denial categories.** Blanket appealing nets
   $22K. Appealing only positive-ROI categories nets $288K — a 13x difference from
   the same denial pool, achieved by *not* working the other five.
3. **Fix our denial reason data before setting category-level targets.** 60% of
   denials are reported as unclassified, which caps how precisely we can target
   anything.

---

## The finding

Five plan years of CMS Transparency in Coverage data — 277 issuers, 1.88 billion
commercial Exchange claims — establish the industry baseline:

| Stage | Volume | Rate |
|---|---|---|
| Claims received | 1.88B | — |
| Claims denied | 359M | **19.1%** |
| Denials reworked and resubmitted | 90M | 33.5% of denials, 2022–24 only \* |
| Denials formally appealed | 901K | **0.25% of denials** |
| Appeals overturned | 358K | **39.7% of appeals filed** |

\* Every other row pools all five experience years. Resubmission cannot: CMS did not
collect it before the PY2024 file, so 2020 and 2021 are blank. The 33.5% is
89,838,810 resubmissions over the 268,166,835 denials in the three reporting years.
Dividing the same volume by the five-year denial pool would give 25.0%, which is not a
resubmission rate. In 2024 alone the rate was 34.7%.

**Almost nobody appeals, and appeals usually work.** 99.75% of denials are never
challenged, while roughly two in five that are challenged get overturned. On its face
that looks like a large, obvious pot of money.

It is not, and the reason matters.

### Why "appeal everything" fails

An appeal costs analyst and clinical time. Once the cost of obtaining recovery is
netted against its expected value, only **five of ten** denial categories return more
than they consume:

| Denial category | Root cause | Owner | Appeal ROI | Recommended |
|---|---|---|---|---|
| Member not covered | Front-End: Eligibility & Network Verification | Patient Access | 3.30 | Appeal |
| Administrative reason | Mid-Cycle: Coding & Claim Submission | HIM / Coding | 2.20 | Appeal |
| Referral required | Front-End: Authorization & Referral | Patient Access | 1.65 | Appeal |
| Benefit limit reached | Benefit Design: Benefit Maximum Reached | Contracting | 1.65 | Appeal |
| Out of network | Front-End: Eligibility & Network Verification | Patient Access | 1.10 | Appeal |
| Other | Unclassified | Revenue Integrity | 0.83 | Do not appeal |
| Service excluded | Benefit Design: Contractual Exclusion | Contracting | 0.83 | Do not appeal |
| Not medically necessary | Clinical: Medical Necessity | Clinical Documentation | 0.55 | Do not appeal |
| Not medically necessary (behavioral) | Clinical: Medical Necessity (Behavioral) | Clinical Documentation | 0.47 | Do not appeal |
| Investigational / experimental | Clinical: Coverage Policy | Utilization Management | 0.41 | Do not appeal |

The pattern is consistent: **low-effort administrative appeals pay; high-effort
clinical appeals on mid-value claims do not.** A medical necessity appeal consumes
around three hours of analyst and clinical reviewer time. At our average claim value
that work costs more than the expected recovery.

This is why a blanket "raise our appeal rate" initiative would consume real capacity
and return almost nothing. The recommendation is the opposite of the intuition.

### Where the money actually is

| Lever | Annual value | Share |
|---|---|---|
| Denial prevention | $5,063,865 | 95% |
| Selective appeal recovery | $287,651 | 5% |
| **Total** | **$5,351,516** | |

A prevented denial never incurs rework cost and never enters the write-off pool. A
recovered denial has already consumed rework and appeal labour before it pays. At our
volume, prevention is worth **18x** recovery.

### Prioritized action list

| Wave | Root cause | Owner | Annual value |
|---|---|---|---|
| **1 (0–90 days)** | Unclassified | Revenue Integrity | $2,525,395 |
| **1 (0–90 days)** | Mid-Cycle: Coding & Claim Submission | HIM / Coding | $1,479,534 |
| 2 (90–180 days) | Front-End: Authorization & Referral | Patient Access | $515,338 |
| 2 (90–180 days) | Front-End: Eligibility & Network Verification | Patient Access | $382,558 |
| 3 (180+ days) | Benefit Design and Clinical categories | Contracting, CDI, UM | $448,691 |

Wave 1 carries $4.0M, 75% of the total.

---

## The constraint that limits everything above

**60% of denials are reported as "Other."**

The largest single denial category cannot be assigned a root cause or an owner. The
$2.5M sitting in Wave 1 "Unclassified" is real money, but we cannot yet say which
process creates it.

This is the highest-leverage thing to fix, and it is not an analytics problem. It
requires pulling CARC/RARC detail from our own 835 remittance files rather than
relying on payer-published summary categories. Until then, category-level prevention
targets below the Wave 1 level carry more precision than the underlying data supports.

**Recommendation:** commission the 835 extract (open item OI-01) before committing to
departmental denial-reduction targets.

---

## How defensible is $5.4M

The figure rests on observed rates and six declared assumptions. That separation is
deliberate and is enforced in the model.

**Observed from source data, not adjustable:** denial rate, resubmission rate, appeal
rate, overturn rate, denial reason mix. These are what 277 issuers reported to CMS.

**The six declared assumptions**, each with a stated range, are: average allowed amount
per claim, appeal cost per hour, collection rate on overturn, resubmission success rate,
rework touch cost, and value at risk per denial. The per-category preventability and
effort weights are a seventh input carrying RCM domain judgement; they are adjustable in
the model but are not part of the six-parameter sensitivity sweep.

The first of the six — **average allowed amount per claim, $1,336** — is derived rather
than estimated: built from CMS DY2024 inpatient, outpatient, and physician payment files
across 1.51 million rows in three source files, weighted by a four-bucket claim mix and
adjusted to commercial rates.

### Which rates the dollar model uses

The $5.35M is computed on **2024 rates**, not the pooled five-year rates in the table
above. This is deliberate — a forward-looking recovery model should reflect current
payer behaviour, and the pooled series includes COVID-distorted 2020–21 — but the two
must not be mixed:

| Measure | Pooled 2020–24 (baseline above) | 2024 (drives the dollar model) |
|---|---|---|
| Denial rate | 19.1% | 20.4% |
| Appeal rate | 0.25% | 0.26% |
| Overturn rate | 39.7% | **32.6%** |

The overturn gap is the one that matters. The headline "roughly two in five appeals
succeed" is the pooled historical rate; the model prices recovery at the 2024 rate of
32.6%, which is the more conservative of the two. Reproducing the model from the pooled
rates will not give $5.35M.

### Sensitivity

Stress-testing every assumption across its full declared range:

| | Total opportunity |
|---|---|
| Low case | $3.17M |
| **Base case** | **$5.35M** |
| High case | $9.02M |

The most load-bearing assumption is **value at risk per denial**. That was identified
by the sensitivity analysis itself, which is why the second-most load-bearing input —
claim value — was replaced with a derivation from published CMS data rather than left
as an estimate.

### Calibration

Finance declined to accept a figure defended only by its own inputs. The model is
therefore anchored externally: modelled denial loss must fall inside the published
**3–5% of net patient revenue** band that the industry reports.

> Modelled denial loss: **4.12%** of gross claim value. **Within band.**

This check runs on every pipeline execution and every dashboard interaction. If an
assumption is moved far enough to push the model outside the band, the dashboard
displays a calibration failure rather than quietly reporting a larger number. The
model can be wrong, but it cannot be wrong quietly.

### What would change the answer

| If this were false | Effect |
|---|---|
| Our payer mix resembles the national Exchange cohort | Rates need recalibration against our own 835 data; direction of the finding is unlikely to change |
| Resubmission succeeds ~55% of the time | The only funnel stage not observed. Directly scales prevention value; open item OI-04 |
| Front-end denials are 70–90% preventable | Patient Access flagged that eligibility verification is partly vendor-performed, which may cap achievable prevention; open item OI-02 |

---

## What I need

1. **Decision** on funding Wave 1 prevention work in HIM/Coding and Revenue Integrity.
2. **Approval** to commission the 835 remittance extract (OI-01) — this unlocks the
   $2.5M currently unattributable.
3. **Sign-off from Finance** on the $5.4M figure and the 4.12% calibration, so the
   organization stops quoting three different denial-loss numbers.
4. **Confirmation from Patient Access** on the vendor SLA constraint (OI-02).

---

### Appendix — reproducing this analysis

```bash
python run_pipeline.py     # ingest, harmonize, derive, analyze, build star schema
python tests/test_uat.py   # 23 acceptance tests
streamlit run app.py       # dashboard with every assumption exposed as a control
```

All source data is public. No protected health information is used at any stage.
