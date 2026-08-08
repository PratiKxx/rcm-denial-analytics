"""
Claims Denial Analytics & Recovery Model - interactive dashboard.

Every assumption in the recovery model is exposed as a control. The point is not
to defend one dollar figure but to let a reviewer move the inputs and see where
the conclusion holds and where it breaks.

Run:  streamlit run app.py
"""
import json
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from analyze import (calibration_check, national_funnel, prioritize,  # noqa: E402
                     reason_mix, recovery_model)
from config import (ASSUMPTIONS, OUTPUTS, PROCESSED, PROVIDER_PROFILE)  # noqa: E402

st.set_page_config(page_title="Claims Denial Analytics & Recovery Model",
                   page_icon="📉", layout="wide")

TEAL, CORAL, SLATE = "#1B9AAA", "#EF6461", "#4A5568"
PALETTE = ["#1B9AAA", "#EF6461", "#F4A261", "#5C6F82", "#2A9D8F",
           "#E9C46A", "#8E7DBE", "#7BA05B", "#C77DFF", "#B0B7C3"]


@st.cache_data
def load():
    plan = pd.read_parquet(PROCESSED / "plan_panel.parquet")
    iss = pd.read_parquet(PROCESSED / "issuer_panel.parquet")
    dq = pd.read_csv(OUTPUTS / "dq_log.csv")
    recon = pd.read_csv(OUTPUTS / "reconciliation.csv")
    cv = json.loads((OUTPUTS / "claim_value.json").read_text())
    cvd = pd.read_csv(OUTPUTS / "claim_value_derivation.csv")
    return plan, iss, dq, recon, cv, cvd


plan, iss, dq, recon, claim_value, claim_value_deriv = load()
funnel = national_funnel(iss)
mix = reason_mix(plan)

st.title("Claims Denial Analytics & Recovery Model")
st.caption(
    f"CMS Transparency in Coverage PUF, plan years 2022-2026 "
    f"({int(funnel.experience_year.min())}-{int(funnel.experience_year.max())} experience) · "
    f"{iss['issuer_id'].nunique()} issuers · {len(plan):,} plan-years · "
    f"{plan['state'].nunique()} states · all denial, appeal and overturn rates observed"
)

# ---------------------------------------------------------------- sidebar
st.sidebar.header("Provider scale")
claims = st.sidebar.number_input(
    "Annual marketplace claims", 10_000, 5_000_000,
    PROVIDER_PROFILE["annual_marketplace_claims"], step=1_000,
    help="All findings are rates, so they rescale to any claim volume.")

st.sidebar.header("Model assumptions")
st.sidebar.caption("Observed rates are fixed. Only these are adjustable.")
A = {}
for k, spec in ASSUMPTIONS.items():
    label = k.replace("_", " ").capitalize()
    lo, hi, val = float(spec["low"]), float(spec["high"]), float(spec["value"])
    step = max((hi - lo) / 100.0, 0.001)
    A[k] = st.sidebar.slider(label, lo, hi, val, step=step, help=spec["source"])

provider = {**PROVIDER_PROFILE, "annual_marketplace_claims": claims}
rec = recovery_model(mix, funnel, assumptions=A, provider=provider)
prio = prioritize(rec)
calib = calibration_check(rec)

latest = funnel.iloc[-1]
all_den = iss["issuer_claims_denied_total"].sum()
all_af = iss["issuer_internal_appeals_filed"].sum()
all_ao = iss["issuer_internal_appeals_overturned"].sum()

# ---------------------------------------------------------------- headline
basis_yr = rec.attrs["rate_basis_year"]
st.markdown(f"##### Industry baseline · pooled {int(funnel.experience_year.min())}–"
            f"{int(funnel.experience_year.max())}")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Claims denied", f"{all_den/1e6:,.0f}M",
          f"{all_den/iss['issuer_claims_received_total'].sum():.1%} of claims received")
c2.metric("Denials appealed", f"{all_af/all_den:.2%}",
          f"{all_den-all_af:,.0f} never appealed", delta_color="inverse")
c3.metric("Appeals overturned", f"{all_ao/all_af:.1%}",
          "when someone does appeal")
c4.metric(f"Annual opportunity · {basis_yr} rates",
          f"${rec['total_opportunity_selective'].sum()/1e6:,.2f}M",
          f"{provider['annual_marketplace_claims']:,} claims/yr")

st.caption(
    f"**The first three tiles and the fourth are on different bases, deliberately.** "
    f"The baseline tiles pool {int(funnel.experience_year.min())}–"
    f"{int(funnel.experience_year.max())}. The dollar model is driven by "
    f"**{basis_yr} rates only** — denial {rec.attrs['rate_basis']['denial_rate']:.1%}, "
    f"overturn {rec.attrs['rate_basis']['internal_overturn_rate']:.1%} — because a "
    f"forward-looking recovery model should reflect current payer behaviour, and the "
    f"pooled series includes COVID-distorted 2020–21. The {basis_yr} overturn rate is "
    f"the more conservative of the two.")

if calib["status"] == "PASS":
    st.success(
        f"**Calibration PASS** — modelled denial loss is "
        f"{calib['denial_loss_pct_of_revenue']:.2%} of gross claim value, inside the "
        f"published {calib['benchmark_low']:.0%}–{calib['benchmark_high']:.0%} of net "
        f"patient revenue band. The dollar model is anchored to an external benchmark, "
        f"not just to its own assumptions.")
else:
    st.error(
        f"**Calibration FAIL** — modelled denial loss is "
        f"{calib['denial_loss_pct_of_revenue']:.2%} of gross claim value, outside the "
        f"published {calib['benchmark_low']:.0%}–{calib['benchmark_high']:.0%} band. "
        f"The current assumption set is not defensible; move the sliders back toward "
        f"their base values.")

tabs = st.tabs(["Denial funnel", "Root cause & priority", "Payer scorecard",
                "Geography", "Data quality", "Method"])

# ---------------------------------------------------------------- funnel
with tabs[0]:
    st.subheader("The denial-to-recovery funnel")
    st.markdown(
        f"Across {int(funnel.experience_year.min())}–{int(funnel.experience_year.max())}, "
        f"issuers denied **{all_den/1e6:,.0f} million** claims. "
        f"**{all_af/all_den:.2%}** were appealed. Of those, **{all_ao/all_af:.1%}** were "
        f"overturned. The gap between how rarely denials are challenged and how often "
        f"challenges succeed is the core finding of this analysis.")

    stages = ["Claims received", "Claims denied", "Resubmitted", "Appealed", "Overturned"]
    vals = [iss["issuer_claims_received_total"].sum(), all_den,
            iss["issuer_claims_resubmitted_total"].sum(), all_af, all_ao]
    fig = go.Figure(go.Funnel(
        y=stages, x=vals, textinfo="value+percent initial",
        marker=dict(color=[TEAL, CORAL, "#F4A261", SLATE, "#2A9D8F"])))
    fig.update_layout(height=420, margin=dict(t=10, b=10))
    st.plotly_chart(fig, width="stretch")

    st.subheader("Trend by experience year")
    f2 = funnel.copy()
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=f2.experience_year, y=f2.denial_rate * 100,
                              name="Denial rate %", mode="lines+markers",
                              line=dict(color=CORAL, width=3)))
    fig2.add_trace(go.Scatter(x=f2.experience_year, y=f2.internal_overturn_rate * 100,
                              name="Overturn rate %", mode="lines+markers",
                              line=dict(color=TEAL, width=3)))
    fig2.add_trace(go.Bar(x=f2.experience_year, y=f2.appeal_rate * 100,
                          name="Appeal rate %", marker_color=SLATE, opacity=0.55,
                          yaxis="y2"))
    fig2.update_layout(
        height=400, yaxis=dict(title="Denial / overturn rate (%)"),
        yaxis2=dict(title="Appeal rate (%)", overlaying="y", side="right"),
        legend=dict(orientation="h", y=1.12), margin=dict(t=40, b=10))
    st.plotly_chart(fig2, width="stretch")

    show = f2[["experience_year", "issuers", "claims_received", "claims_denied",
               "denial_rate", "resubmission_rate", "appeal_rate",
               "internal_overturn_rate", "external_overturn_rate"]].copy()
    for c in ("denial_rate", "resubmission_rate", "appeal_rate",
              "internal_overturn_rate", "external_overturn_rate"):
        show[c] = (show[c] * 100).round(2)
    st.dataframe(show, width="stretch", hide_index=True)

# ---------------------------------------------------------------- root cause
with tabs[1]:
    st.subheader("Where denials originate, and what to do about them")

    other = mix.loc[mix.denial_reason == "den_other", "share_of_denials"].iloc[0]
    st.warning(
        f"**{other:.0%} of denials are reported as \"Other\".** Root-cause "
        f"management is structurally limited by the payer reason taxonomy itself. "
        f"Recommendation BRD-021 addresses this: require CARC/RARC-level detail in "
        f"payer remittance before committing to category-level prevention targets.")

    d = rec.sort_values("total_opportunity_selective", ascending=False)
    fig3 = go.Figure()
    fig3.add_trace(go.Bar(y=d.root_cause, x=d.prevention_value, name="Prevention value",
                          orientation="h", marker_color=TEAL))
    fig3.add_trace(go.Bar(y=d.root_cause, x=d.net_recovery_selective,
                          name="Net appeal recovery", orientation="h", marker_color=CORAL))
    fig3.update_layout(barmode="stack", height=460, xaxis_title="Annual value ($)",
                       legend=dict(orientation="h", y=1.1), margin=dict(t=40, l=10))
    st.plotly_chart(fig3, width="stretch")

    pos = int(rec["appeal_recommended"].sum())
    st.info(
        f"**Appeal selectively, not universally.** Only **{pos} of {len(rec)}** denial "
        f"categories return more than they cost to appeal. Appealing every appealable "
        f"denial nets ${rec['net_recovery'].sum():,.0f}; appealing only the "
        f"positive-ROI categories nets ${rec['net_recovery_selective'].sum():,.0f}. "
        f"Prevention is worth "
        f"{rec['prevention_value'].sum()/max(rec['net_recovery_selective'].sum(),1):,.0f}x "
        f"more than recovery.")

    st.subheader("Prioritized action list")
    p = prio[["rank", "wave", "root_cause", "owner", "denials", "total_opportunity",
              "recovery_probability", "appeal_recommended", "priority_score"]].copy()
    p["denials"] = p["denials"].round(0)
    p["total_opportunity"] = p["total_opportunity"].round(0)
    p["recovery_probability"] = (p["recovery_probability"] * 100).round(1)
    p["priority_score"] = p["priority_score"].round(3)
    st.dataframe(p, width="stretch", hide_index=True,
                 column_config={
                     "total_opportunity": st.column_config.NumberColumn("Annual $", format="$%d"),
                     "recovery_probability": st.column_config.NumberColumn("Recovery prob %"),
                     "appeal_recommended": st.column_config.CheckboxColumn("Appeal?")})

    st.subheader("Detail by denial reason")
    det = rec[["denial_reason", "root_cause", "owner", "x12_carc_examples",
               "share_of_denials", "denials", "appeal_gap", "appeal_roi",
               "net_recovery", "prevention_value", "appeal_recommended"]].copy()
    det["share_of_denials"] = (det["share_of_denials"] * 100).round(1)
    for c in ("denials", "appeal_gap", "net_recovery", "prevention_value"):
        det[c] = det[c].round(0)
    det["appeal_roi"] = det["appeal_roi"].round(2)
    st.dataframe(det.sort_values("prevention_value", ascending=False),
                 width="stretch", hide_index=True)

# ---------------------------------------------------------------- payers
with tabs[2]:
    st.subheader("Payer benchmark")
    st.caption(
        "Payers that both deny heavily and overturn heavily on appeal are the highest "
        "value appeal targets: their denials are frequent and demonstrably soft.")

    yr = int(iss["experience_year"].max())
    d = iss[(iss.experience_year == yr) & (iss.issuer_claims_received_total >= 10_000)].copy()
    d["denial_rate_pct"] = d["denial_rate"] * 100
    d["overturn_pct"] = d["internal_overturn_rate"] * 100

    minc = st.slider("Minimum claims received", 10_000, 2_000_000, 50_000, 10_000)
    dd = d[d.issuer_claims_received_total >= minc].dropna(
        subset=["denial_rate_pct", "overturn_pct"])

    fig4 = go.Figure(go.Scatter(
        x=dd.denial_rate_pct, y=dd.overturn_pct, mode="markers",
        marker=dict(size=(dd.issuer_claims_received_total ** 0.42) / 24,
                    color=dd.denial_rate_pct, colorscale="RdYlBu_r", showscale=True,
                    line=dict(width=1, color="white"),
                    colorbar=dict(title="Denial<br>rate %")),
        text=dd.issuer_name + " (" + dd.state + ")",
        hovertemplate="<b>%{text}</b><br>Denial rate %{x:.1f}%<br>"
                      "Overturn rate %{y:.1f}%<extra></extra>"))
    med_x, med_y = dd.denial_rate_pct.median(), dd.overturn_pct.median()
    fig4.add_vline(x=med_x, line_dash="dash", line_color=SLATE, opacity=0.6)
    fig4.add_hline(y=med_y, line_dash="dash", line_color=SLATE, opacity=0.6)
    fig4.add_annotation(x=dd.denial_rate_pct.max() * 0.95, y=dd.overturn_pct.max() * 0.97,
                        text="<b>Priority appeal targets</b><br>deny often, overturn often",
                        showarrow=False, font=dict(size=11, color=CORAL))
    fig4.update_layout(height=520, xaxis_title=f"Denial rate, {yr} (%)",
                       yaxis_title="Internal appeal overturn rate (%)",
                       margin=dict(t=20))
    st.plotly_chart(fig4, width="stretch")
    st.caption(f"Bubble area is claim volume. Dashed lines mark cohort medians "
               f"({med_x:.1f}% denial, {med_y:.1f}% overturn). n={len(dd)} issuers.")

    tbl = dd[["issuer_name", "state", "issuer_claims_received_total",
              "issuer_claims_denied_total", "denial_rate_pct", "appeal_rate",
              "overturn_pct", "plan_count"]].copy()
    tbl["appeal_rate"] = (tbl["appeal_rate"] * 100).round(3)
    tbl[["denial_rate_pct", "overturn_pct"]] = tbl[["denial_rate_pct", "overturn_pct"]].round(1)
    st.dataframe(tbl.sort_values("denial_rate_pct", ascending=False),
                 width="stretch", hide_index=True)

# ---------------------------------------------------------------- geography
with tabs[3]:
    st.subheader("Denial rate by state")
    yr = int(iss["experience_year"].max())
    g = iss[iss.experience_year == yr].groupby("state", as_index=False).agg(
        issuers=("issuer_id", "nunique"),
        received=("issuer_claims_received_total", "sum"),
        denied=("issuer_claims_denied_total", "sum"),
        filed=("issuer_internal_appeals_filed", "sum"),
        overturned=("issuer_internal_appeals_overturned", "sum"))
    g["denial_rate"] = g.denied / g.received * 100
    g["overturn_rate"] = g.overturned / g.filed.replace(0, pd.NA) * 100
    g = g.dropna(subset=["denial_rate"]).sort_values("denial_rate", ascending=False)

    fig5 = go.Figure(go.Choropleth(
        locations=g.state, locationmode="USA-states", z=g.denial_rate,
        colorscale="RdYlBu_r", colorbar=dict(title="Denial<br>rate %"),
        text=g.state + "<br>" + g.issuers.astype(str) + " issuers",
        hovertemplate="<b>%{text}</b><br>Denial rate %{z:.1f}%<extra></extra>"))
    fig5.update_layout(geo=dict(scope="usa"), height=460, margin=dict(t=10, b=10))
    st.plotly_chart(fig5, width="stretch")
    st.caption(f"{len(g)} states with reporting issuers in {yr}. States absent from the "
               f"map run their own Exchange and do not report to this federal file.")

    fig6 = go.Figure(go.Bar(x=g.state, y=g.denial_rate, marker_color=TEAL))
    fig6.update_layout(height=340, xaxis_title="", yaxis_title="Denial rate (%)",
                       margin=dict(t=10))
    st.plotly_chart(fig6, width="stretch")

# ---------------------------------------------------------------- data quality
with tabs[4]:
    st.subheader("Data quality log")
    st.markdown(
        "Findings raised during harmonization. Severity reflects impact on the "
        "analysis, not on the source file. **DQ-009 is the one that would silently "
        "break a naive build**: issuer-level values repeat across every plan row, so "
        "summing them overstates national claim volume several-fold.")
    sev = st.multiselect("Severity", sorted(dq.severity.unique()),
                         default=sorted(dq.severity.unique()))
    st.dataframe(dq[dq.severity.isin(sev)], width="stretch", hide_index=True)

    st.subheader("Source-to-target reconciliation")
    st.caption("Row counts from each source workbook through to the harmonized panel.")
    st.dataframe(recon, width="stretch", hide_index=True)

    st.subheader("Reason-category reconciliation")
    ok, tot = int(plan.reason_reconciles.sum()), len(plan)
    st.markdown(
        f"Only **{ok:,} of {tot:,}** plan-years ({ok/tot:.0%}) have denial reason "
        f"categories that sum to reported total denials within 2%. Reason-mix analysis "
        f"uses only these rows. Volume analysis uses all rows. Silently rescaling the "
        f"non-reconciling majority would have manufactured precision the source data "
        f"does not support.")
    rr = plan.groupby("plan_year").agg(
        plan_years=("plan_id", "size"), reconciling=("reason_reconciles", "sum")).reset_index()
    rr["pct"] = (rr.reconciling / rr.plan_years * 100).round(1)
    st.dataframe(rr, width="stretch", hide_index=True)

# ---------------------------------------------------------------- method
with tabs[5]:
    st.subheader("What is observed and what is assumed")
    st.markdown(
        "The credibility of the dollar figure rests entirely on this separation.")
    obs = pd.DataFrame([
        ("Denial rate", f"{latest.denial_rate:.1%}", "Observed", "TC-PUF issuer reports"),
        ("Resubmission rate", f"{latest.resubmission_rate:.1%}", "Observed", "TC-PUF issuer reports"),
        ("Appeal rate", f"{latest.appeal_rate:.3%}", "Observed", "TC-PUF issuer reports"),
        ("Internal overturn rate", f"{latest.internal_overturn_rate:.1%}", "Observed", "TC-PUF issuer reports"),
        ("Denial reason mix", f"{len(mix)} categories", "Observed", "TC-PUF plan-level reports"),
        ("Allowed amount per claim", f"${A['avg_allowed_amount_per_claim']:,.0f}",
         "Derived", "CMS DY2024 payment files, 4-bucket mix"),
        ("Resubmission success rate", f"{A['resubmission_success_rate']:.0%}", "Assumed",
         "Outcome not published in TC-PUF"),
        ("Value at risk per denial", f"{A['denial_value_at_risk_share']:.0%}", "Assumed",
         "Calibrated to 3-5% of revenue benchmark"),
        ("Preventability / appealability", "per category", "Assumed", "RCM domain judgement"),
    ], columns=["Input", "Value", "Basis", "Source"])
    st.dataframe(obs, width="stretch", hide_index=True)

    st.subheader("Claim value derivation")
    st.caption("Sensitivity identified this as the most load-bearing assumption, so it "
               "is derived from CMS payment data rather than asserted.")
    cvd = claim_value_deriv[["setting", "medicare_allowed_per_unit", "unit",
                             "units_per_claim", "commercial_multiplier",
                             "commercial_allowed_per_claim", "claim_mix_share",
                             "weighted_contribution"]].copy()
    st.dataframe(cvd.round(2), width="stretch", hide_index=True)
    st.caption(
        "The CMS outpatient file covers **Comprehensive APCs only** — 72 procedural APC "
        "groups, 68 of which carry a priced row, averaging $5,123 per service. "
        "Treating that as the outpatient average "
        "overstates blended claim value roughly tenfold, so outpatient is split into "
        "procedural and ancillary buckets. See DQ-010.")

    st.subheader("Sensitivity")
    rows = []
    base = rec["total_opportunity_selective"].sum()
    for k, spec in ASSUMPTIONS.items():
        for scen in ("low", "high"):
            a = dict(A); a[k] = spec[scen]
            t = recovery_model(mix, funnel, assumptions=a,
                               provider=provider)["total_opportunity_selective"].sum()
            rows.append(dict(assumption=k, scenario=scen, value=spec[scen],
                             total=t, pct_delta=(t - base) / base * 100))
    sdf = pd.DataFrame(rows)
    order = sdf.groupby("assumption")["pct_delta"].apply(
        lambda s: s.abs().max()).sort_values().index.tolist()
    fig7 = go.Figure()
    for scen, col in [("low", CORAL), ("high", TEAL)]:
        s = sdf[sdf.scenario == scen].set_index("assumption").loc[order].reset_index()
        fig7.add_trace(go.Bar(y=s.assumption, x=s.pct_delta, name=scen,
                              orientation="h", marker_color=col))
    fig7.update_layout(barmode="overlay", height=380, xaxis_title="Change in total opportunity (%)",
                       legend=dict(orientation="h", y=1.12), margin=dict(t=40, l=10))
    st.plotly_chart(fig7, width="stretch")
    st.caption(f"Base case ${base/1e6:,.2f}M. Tornado ordered by swing magnitude.")

    st.subheader("Provenance")
    st.markdown(f"""
- **CMS Transparency in Coverage PUF**, plan years 2022–2026, individual market QHP sheets.
  Issuer self-reported claims, denials, appeals, and enrollment. Downloaded from
  `data.healthcare.gov`. Five plan years spanning three schema generations, harmonized
  into one canonical model; see `docs/DATA_DICTIONARY.md`.
- **CMS Medicare Inpatient Hospitals by Provider and Service**, DY2024
  ({claim_value['observed_source_rows']['inpatient']:,} rows).
- **CMS Medicare Outpatient Hospitals by Provider and Service**, DY2024
  ({claim_value['observed_source_rows']['outpatient_procedural']:,} rows, C-APC only).
- **CMS Medicare Physician & Other Practitioners by Provider**, DY2024
  ({claim_value['observed_source_rows']['professional']:,} rows).

TC-PUF is **payer self-reported** and covers federally-facilitated Exchange plans only.
It is not a provider claims extract, and no patient-level or PHI data is used anywhere
in this project.
""")
