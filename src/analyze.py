"""
Stage 03 - Denial funnel, root-cause attribution, recovery model, prioritization.

The funnel is observed, not assumed. Denial, resubmission, appeal, and overturn
rates all come directly from issuer-reported TC-PUF values. Only the dollar
conversion and the effort/preventability weights are assumptions, and each one
is declared in config.ASSUMPTIONS and stress-tested in outputs/sensitivity.csv.

Outputs
    outputs/funnel_national.csv        national denial-to-recovery funnel by year
    outputs/root_cause_summary.csv     denial volume and recoverable value by root cause
    outputs/issuer_scorecard.csv       per-payer benchmark with peer percentiles
    outputs/state_summary.csv          geographic view
    outputs/prioritization.csv         ranked action list for the reference provider
    outputs/sensitivity.csv            one-at-a-time assumption stress test
    outputs/headline_metrics.json      figures cited in the executive memo
"""
import json

import numpy as np
import pandas as pd

from config import (ASSUMPTIONS, CALIBRATION_BAND_PCT_OF_REVENUE,
                    DENIAL_REASON_COLS, MIN_APPEALS_FOR_RATE, OUTPUTS, PROCESSED,
                    PROVIDER_PROFILE, ROOT_CAUSE_TAXONOMY)


def _rate(num, den):
    den = float(den)
    return float(num) / den if den else np.nan


def national_funnel(iss):
    """Denial-to-recovery funnel by experience year, all observed."""
    rows = []
    for yr, d in iss.groupby("experience_year"):
        recv = d["issuer_claims_received_total"].sum()
        den = d["issuer_claims_denied_total"].sum()
        resub = d["issuer_claims_resubmitted_total"].sum(min_count=1)
        af = d["issuer_internal_appeals_filed"].sum()
        ao = d["issuer_internal_appeals_overturned"].sum()
        ef = d["issuer_external_appeals_filed"].sum()
        eo = d["issuer_external_appeals_overturned"].sum()
        rows.append(dict(
            experience_year=int(yr), issuers=d["issuer_id"].nunique(),
            claims_received=recv, claims_denied=den,
            denial_rate=_rate(den, recv),
            claims_resubmitted=resub, resubmission_rate=_rate(resub, den),
            internal_appeals_filed=af, appeal_rate=_rate(af, den),
            internal_appeals_overturned=ao, internal_overturn_rate=_rate(ao, af),
            external_appeals_filed=ef, external_appeals_overturned=eo,
            external_overturn_rate=_rate(eo, ef),
            denials_never_appealed=den - af,
            share_denials_never_appealed=_rate(den - af, den),
        ))
    return pd.DataFrame(rows).sort_values("experience_year")


def reason_mix(plan):
    """
    National denial reason mix, computed only on plan-years whose reason
    categories reconcile to reported total denials. Non-reconciling rows are
    excluded rather than silently rescaled.
    """
    sub = plan[plan["reason_reconciles"]]
    tot = sub[DENIAL_REASON_COLS].sum()
    mix = (tot / tot.sum()).rename("share_of_denials")
    out = mix.reset_index().rename(columns={"index": "denial_reason"})
    out["denials_observed"] = out["denial_reason"].map(tot)
    meta = pd.DataFrame(ROOT_CAUSE_TAXONOMY).T.reset_index().rename(columns={"index": "denial_reason"})
    out = out.merge(meta, on="denial_reason", how="left")
    for c in ("preventability", "appealability", "effort_hours"):
        out[c] = out[c].astype(float)
    out["basis_plan_years"] = len(sub)
    return out.sort_values("share_of_denials", ascending=False)


def recovery_model(mix, funnel, assumptions=None, provider=None):
    """
    Recoverable value for one provider organization, by root cause.

    For each denial reason:
        denials         = provider claims x national denial rate x reason share
        appealable      = denials x appealability
        already_appealed= denials x observed appeal rate
        appeal_gap      = appealable - already_appealed   (the actionable pool)
        recovered       = appeal_gap x observed overturn rate
        gross_recovery  = recovered x allowed amount x collection rate
        appeal_cost     = appeal_gap x effort hours x hourly cost
        net_recovery    = gross_recovery - appeal_cost

    Prevention is valued separately: a denial prevented at source never incurs
    rework cost and never enters the write-off pool.

    RATE BASIS — read this before comparing to any headline figure.

    The model is driven by the MOST RECENT experience year, not the pooled
    five-year average. That is deliberate: a forward-looking recovery model
    should reflect current payer behaviour, and the pooled series includes
    2020-2021, whose utilisation was distorted by COVID.

    The consequence is that the model's rates differ from the pooled rates
    quoted as the industry baseline, and the two must not be mixed:

        measure          pooled 2020-2024    model basis (2024)
        denial rate            19.1%               20.4%
        appeal rate             0.25%               0.26%
        overturn rate          39.7%               32.6%

    The overturn gap matters most: the pooled 39.7% is the right number for
    "how often do appeals succeed historically", but the model prices recovery
    at the 2024 rate of 32.6%, which is the conservative choice. Every consumer
    of this function reports the basis via rec.attrs["rate_basis_year"].
    """
    A = assumptions or {k: v["value"] for k, v in ASSUMPTIONS.items()}
    P = provider or PROVIDER_PROFILE
    latest = funnel.sort_values("experience_year").iloc[-1]

    claims = P["annual_marketplace_claims"]
    denial_rate = latest["denial_rate"]
    appeal_rate = latest["appeal_rate"]
    overturn = latest["internal_overturn_rate"]
    resub_rate = latest["resubmission_rate"]

    total_denials = claims * denial_rate
    # Share of denied value ultimately lost: not recovered by rework, not by appeal.
    recovered_by_rework = resub_rate * A["resubmission_success_rate"]
    recovered_by_appeal = appeal_rate * overturn
    write_off_share = max(0.0, 1.0 - recovered_by_rework - recovered_by_appeal)

    # Value genuinely at risk on a denied claim, not its full allowed amount.
    at_risk = A["avg_allowed_amount_per_claim"] * A["denial_value_at_risk_share"]

    rows = []
    for _, r in mix.iterrows():
        den = total_denials * r["share_of_denials"]
        appealable = den * r["appealability"]
        already = den * appeal_rate
        gap = max(0.0, appealable - already)
        recovered = gap * overturn
        gross = recovered * at_risk * A["collection_rate_on_overturn"]
        cost = gap * r["effort_hours"] * A["appeal_cost_per_hour"]
        net = gross - cost

        preventable = den * r["preventability"]
        prevention_value = (preventable * at_risk * write_off_share
                            + preventable * resub_rate * A["rework_touch_cost"])

        rows.append(dict(
            denial_reason=r["denial_reason"], root_cause=r["root_cause"],
            owner=r["owner"], x12_carc_examples=r["x12_carc_examples"],
            share_of_denials=r["share_of_denials"], denials=den,
            appealable_denials=appealable, currently_appealed=already,
            appeal_gap=gap, expected_overturned=recovered,
            gross_recovery=gross, appeal_cost=cost, net_recovery=net,
            appeal_roi=gross / cost if cost > 0 else np.nan,
            preventable_denials=preventable, prevention_value=prevention_value,
            total_opportunity=net + prevention_value,
        ))
    df = pd.DataFrame(rows)
    # Appealing every appealable denial is close to break-even: high-effort
    # clinical categories consume more analyst time than they return. Only
    # categories that clear a 1.0 ROI threshold are recommended for appeal.
    df["appeal_recommended"] = df["appeal_roi"] > 1.0
    df["net_recovery_selective"] = df["net_recovery"].where(df["appeal_recommended"], 0.0)
    df["total_opportunity_selective"] = df["net_recovery_selective"] + df["prevention_value"]
    df.attrs["write_off_share"] = write_off_share
    df.attrs["total_denials"] = total_denials
    df.attrs["at_risk_per_denial"] = at_risk
    # Basis disclosure, so no consumer can report the dollar figure without it.
    df.attrs["rate_basis_year"] = int(latest["experience_year"])
    df.attrs["rate_basis"] = dict(
        denial_rate=float(denial_rate), appeal_rate=float(appeal_rate),
        internal_overturn_rate=float(overturn), resubmission_rate=float(resub_rate))
    df.attrs["gross_claim_value"] = claims * A["avg_allowed_amount_per_claim"]
    df.attrs["denial_write_off"] = total_denials * write_off_share * at_risk
    df.attrs["denial_loss_pct_of_revenue"] = (
        df.attrs["denial_write_off"] / df.attrs["gross_claim_value"])
    return df


def calibration_check(rec):
    """
    Modelled denial loss must land inside the published 3-5 percent of net
    patient revenue band. Outside it, the assumption set is wrong regardless of
    how defensible each individual parameter looks.
    """
    pct = rec.attrs["denial_loss_pct_of_revenue"]
    lo, hi = CALIBRATION_BAND_PCT_OF_REVENUE
    status = "PASS" if lo <= pct <= hi else "FAIL"
    return {
        "gross_claim_value": rec.attrs["gross_claim_value"],
        "denial_write_off": rec.attrs["denial_write_off"],
        "denial_loss_pct_of_revenue": pct,
        "benchmark_low": lo, "benchmark_high": hi, "status": status,
    }


def prioritize(rec):
    """
    Rank root causes by a composite score. Value and effort are both normalized
    to 0-1 within the cohort so the score is scale-free and re-ranks correctly
    when the reader changes the provider volume.
    """
    d = rec.groupby(["root_cause", "owner"], as_index=False).agg(
        denials=("denials", "sum"), appeal_gap=("appeal_gap", "sum"),
        net_recovery=("net_recovery", "sum"), prevention_value=("prevention_value", "sum"),
        total_opportunity=("total_opportunity_selective", "sum"),
        net_recovery_selective=("net_recovery_selective", "sum"),
        appeal_cost=("appeal_cost", "sum"),
        expected_overturned=("expected_overturned", "sum"),
        appeal_recommended=("appeal_recommended", "any"))
    d["recovery_probability"] = d["expected_overturned"] / d["appeal_gap"].replace(0, np.nan)
    d["effort_hours"] = d["appeal_cost"] / ASSUMPTIONS["appeal_cost_per_hour"]["value"]

    def norm(s):
        rng = s.max() - s.min()
        return (s - s.min()) / rng if rng else pd.Series(0.5, index=s.index)

    d["value_score"] = norm(d["total_opportunity"])
    d["ease_score"] = 1 - norm(d["effort_hours"])
    d["prob_score"] = norm(d["recovery_probability"].fillna(0))
    # Value dominates; probability and ease break ties between comparable pools.
    d["priority_score"] = (0.55 * d["value_score"] + 0.25 * d["prob_score"]
                           + 0.20 * d["ease_score"])
    d = d.sort_values("priority_score", ascending=False).reset_index(drop=True)
    d.insert(0, "rank", d.index + 1)
    d["wave"] = np.where(d["rank"] <= 2, "Wave 1 (0-90 days)",
                np.where(d["rank"] <= 4, "Wave 2 (90-180 days)", "Wave 3 (180+ days)"))
    return d


def issuer_scorecard(iss):
    """Per-payer benchmark on the most recent experience year with peer percentiles."""
    yr = iss["experience_year"].max()
    d = iss[iss["experience_year"] == yr].copy()
    d = d[d["issuer_claims_received_total"] >= 10_000]

    d["pct_denial_rate"] = d["denial_rate"].rank(pct=True)
    d["pct_appeal_rate"] = d["appeal_rate"].rank(pct=True)
    d["pct_overturn_rate"] = d["internal_overturn_rate"].rank(pct=True)

    med = d["denial_rate"].median()
    d["excess_denial_rate"] = d["denial_rate"] - med
    d["excess_denials_vs_median"] = d["excess_denial_rate"] * d["issuer_claims_received_total"]

    # A payer that denies heavily and overturns heavily on appeal is the highest
    # value appeal target: the denials are both frequent and demonstrably soft.
    d["appeal_target_score"] = (d["pct_denial_rate"].fillna(0)
                                * d["pct_overturn_rate"].fillna(0))
    cols = ["experience_year", "issuer_id", "issuer_name", "state", "plan_count",
            "issuer_claims_received_total", "issuer_claims_denied_total", "denial_rate",
            "pct_denial_rate", "issuer_internal_appeals_filed", "appeal_rate",
            "pct_appeal_rate", "internal_overturn_rate", "pct_overturn_rate",
            "external_overturn_rate", "excess_denial_rate", "excess_denials_vs_median",
            "appeal_target_score"]
    return d[cols].sort_values("appeal_target_score", ascending=False)


def state_summary(iss):
    yr = iss["experience_year"].max()
    d = iss[iss["experience_year"] == yr]
    g = d.groupby("state", as_index=False).agg(
        issuers=("issuer_id", "nunique"),
        claims_received=("issuer_claims_received_total", "sum"),
        claims_denied=("issuer_claims_denied_total", "sum"),
        appeals_filed=("issuer_internal_appeals_filed", "sum"),
        appeals_overturned=("issuer_internal_appeals_overturned", "sum"))
    g["denial_rate"] = g["claims_denied"] / g["claims_received"]
    g["appeal_rate"] = g["appeals_filed"] / g["claims_denied"]
    g["overturn_rate"] = g["appeals_overturned"] / g["appeals_filed"].replace(0, np.nan)
    g["experience_year"] = yr
    return g.sort_values("denial_rate", ascending=False)


def sensitivity(mix, funnel):
    """One-at-a-time stress test across each assumption's stated low/high bound."""
    base_rec = recovery_model(mix, funnel)
    base = base_rec["total_opportunity_selective"].sum()
    rows = [dict(assumption="BASE CASE", scenario="base", value=np.nan,
                 total_opportunity=base, pct_change=0.0)]
    for name, spec in ASSUMPTIONS.items():
        for scen in ("low", "high"):
            a = {k: v["value"] for k, v in ASSUMPTIONS.items()}
            a[name] = spec[scen]
            tot = recovery_model(mix, funnel, assumptions=a)["total_opportunity_selective"].sum()
            rows.append(dict(assumption=name, scenario=scen, value=spec[scen],
                             total_opportunity=tot, pct_change=(tot - base) / base))
    df = pd.DataFrame(rows)
    df["abs_pct"] = df["pct_change"].abs()
    swing = (df[df.assumption != "BASE CASE"].groupby("assumption")["abs_pct"].max()
             .sort_values(ascending=False).rename("max_swing").reset_index())
    df = df.merge(swing, on="assumption", how="left")
    return df.sort_values(["max_swing", "assumption", "scenario"],
                          ascending=[False, True, True]).drop(columns="abs_pct")


def main():
    plan = pd.read_parquet(PROCESSED / "plan_panel.parquet")
    iss = pd.read_parquet(PROCESSED / "issuer_panel.parquet")

    funnel = national_funnel(iss)
    mix = reason_mix(plan)
    rec = recovery_model(mix, funnel)
    calib = calibration_check(rec)
    pd.DataFrame([calib]).to_csv(OUTPUTS / "calibration_check.csv", index=False)
    prio = prioritize(rec)
    score = issuer_scorecard(iss)
    states = state_summary(iss)
    sens = sensitivity(mix, funnel)

    funnel.to_csv(OUTPUTS / "funnel_national.csv", index=False)
    rec.to_csv(OUTPUTS / "root_cause_summary.csv", index=False)
    prio.to_csv(OUTPUTS / "prioritization.csv", index=False)
    score.to_csv(OUTPUTS / "issuer_scorecard.csv", index=False)
    states.to_csv(OUTPUTS / "state_summary.csv", index=False)
    sens.to_csv(OUTPUTS / "sensitivity.csv", index=False)
    mix.to_csv(OUTPUTS / "reason_mix.csv", index=False)

    latest = funnel.iloc[-1]
    _resub_sub = funnel.dropna(subset=["claims_resubmitted"])
    allyr_den = iss["issuer_claims_denied_total"].sum()
    allyr_af = iss["issuer_internal_appeals_filed"].sum()
    allyr_ao = iss["issuer_internal_appeals_overturned"].sum()

    head = {
        "data_vintage": {
            "plan_years": "PY2022-PY2026 files",
            "experience_years": f"{int(funnel.experience_year.min())}-{int(funnel.experience_year.max())}",
            "issuers": int(iss["issuer_id"].nunique()),
            "plan_years_observed": int(len(plan)),
            "states": int(plan["state"].nunique()),
        },
        "national_all_years": {
            "claims_received": float(iss["issuer_claims_received_total"].sum()),
            "claims_denied": float(allyr_den),
            "denial_rate": _rate(allyr_den, iss["issuer_claims_received_total"].sum()),
            "appeal_rate": _rate(allyr_af, allyr_den),
            "internal_overturn_rate": _rate(allyr_ao, allyr_af),
            "denials_never_appealed": float(allyr_den - allyr_af),
            "share_never_appealed": _rate(allyr_den - allyr_af, allyr_den),
        },
        # Resubmission is the one funnel stage not reported in every year: the
        # PY2022/PY2023 files (experience 2020-2021) do not collect it. Its rate
        # must therefore be computed over reporting years only, NOT against the
        # five-year denial pool, or the volume and the rate disagree.
        "resubmission_pooled": {
            "reporting_years": [int(y) for y in
                                funnel.loc[funnel.claims_resubmitted.notna(),
                                           "experience_year"]],
            "claims_resubmitted": float(_resub_sub["claims_resubmitted"].sum()),
            "claims_denied_in_reporting_years": float(_resub_sub["claims_denied"].sum()),
            "resubmission_rate": _rate(_resub_sub["claims_resubmitted"].sum(),
                                       _resub_sub["claims_denied"].sum()),
            "note": "Denominator is denials in the three reporting years only. "
                    "Dividing the same volume by the five-year denial pool gives "
                    "25.0%, which is not a resubmission rate.",
        },
        "latest_year": {
            "experience_year": int(latest["experience_year"]),
            "denial_rate": float(latest["denial_rate"]),
            "resubmission_rate": float(latest["resubmission_rate"]),
            "appeal_rate": float(latest["appeal_rate"]),
            "internal_overturn_rate": float(latest["internal_overturn_rate"]),
        },
        "reason_mix": {
            "unclassified_other_share": float(
                mix.loc[mix.denial_reason == "den_other", "share_of_denials"].iloc[0]),
            "basis_plan_years": int(mix["basis_plan_years"].iloc[0]),
            "top_classified": mix[mix.denial_reason != "den_other"]
                .head(3)[["denial_reason", "share_of_denials"]].to_dict("records"),
        },
        "rate_basis": {
            "note": "The provider dollar model is driven by the most recent experience "
                    "year, NOT the pooled five-year rates quoted as the industry "
                    "baseline. Do not mix the two.",
            "basis_year": rec.attrs["rate_basis_year"],
            "model_rates": rec.attrs["rate_basis"],
            "pooled_rates_for_contrast": {
                "denial_rate": _rate(allyr_den, iss["issuer_claims_received_total"].sum()),
                "appeal_rate": _rate(allyr_af, allyr_den),
                "internal_overturn_rate": _rate(allyr_ao, allyr_af),
            },
        },
        "provider_opportunity": {
            "profile": PROVIDER_PROFILE["name"],
            "annual_claims": PROVIDER_PROFILE["annual_marketplace_claims"],
            "rate_basis_year": rec.attrs["rate_basis_year"],
            "annual_denials": float(rec["denials"].sum()),
            "write_off_share": float(rec.attrs["write_off_share"]),
            "net_appeal_recovery_blanket": float(rec["net_recovery"].sum()),
            "net_appeal_recovery_selective": float(rec["net_recovery_selective"].sum()),
            "categories_appeal_positive": int(rec["appeal_recommended"].sum()),
            "categories_total": int(len(rec)),
            "prevention_value": float(rec["prevention_value"].sum()),
            "total_opportunity": float(rec["total_opportunity_selective"].sum()),
            "prevention_to_appeal_ratio": float(
                rec["prevention_value"].sum() / max(rec["net_recovery_selective"].sum(), 1)),
            "wave1_opportunity": float(
                prio[prio.wave.str.startswith("Wave 1")]["total_opportunity"].sum()),
            "wave1_root_causes": prio[prio.wave.str.startswith("Wave 1")]["root_cause"].tolist(),
        },
        "sensitivity": {
            "range_low": float(sens["total_opportunity"].min()),
            "range_high": float(sens["total_opportunity"].max()),
            "most_sensitive_assumption": sens[sens.assumption != "BASE CASE"]
                .sort_values("max_swing", ascending=False)["assumption"].iloc[0],
        },
        "calibration": calib,
        "assumptions": {k: {"value": v["value"], "low": v["low"], "high": v["high"],
                            "source": v["source"]} for k, v in ASSUMPTIONS.items()},
    }
    (OUTPUTS / "headline_metrics.json").write_text(json.dumps(head, indent=2))

    n = head["national_all_years"]
    o = head["provider_opportunity"]
    print(f"National, PY2022-PY2026 files ({head['data_vintage']['experience_years']} experience)")
    print(f"  {n['claims_received']:>16,.0f}  claims received")
    print(f"  {n['claims_denied']:>16,.0f}  denied ({n['denial_rate']:.1%})")
    print(f"  {n['appeal_rate']*100:>16.3f}%  of denials appealed")
    print(f"  {n['internal_overturn_rate']:>16.1%}  of appeals overturned")
    print(f"  {n['denials_never_appealed']:>16,.0f}  denials never appealed "
          f"({n['share_never_appealed']:.2%})")
    rb = head["rate_basis"]
    print(f"\nRATE BASIS: dollar model uses {rb['basis_year']} rates "
          f"(denial {rb['model_rates']['denial_rate']:.1%}, "
          f"overturn {rb['model_rates']['internal_overturn_rate']:.1%}), NOT the pooled "
          f"{n['denial_rate']:.1%}/{n['internal_overturn_rate']:.1%} baseline above.")
    print(f"\n{o['profile']} ({o['annual_claims']:,} claims/yr)")
    print(f"  {o['annual_denials']:>16,.0f}  annual denials")
    print(f"  ${o['net_appeal_recovery_selective']:>15,.0f}  net appeal recovery (selective, {o['categories_appeal_positive']} of {o['categories_total']} categories)")
    print(f"  ${o['prevention_value']:>15,.0f}  prevention value")
    print(f"  ${o['total_opportunity']:>15,.0f}  TOTAL annual opportunity")
    print(f"  ${head['sensitivity']['range_low']:,.0f} - "
          f"${head['sensitivity']['range_high']:,.0f}  sensitivity range")
    print(f"\nWave 1: {', '.join(o['wave1_root_causes'])}  "
          f"(${o['wave1_opportunity']:,.0f})")
    print(f"\nCALIBRATION [{calib['status']}]  modelled denial loss "
          f"{calib['denial_loss_pct_of_revenue']:.2%} of gross claim value "
          f"vs published benchmark {calib['benchmark_low']:.0%}-{calib['benchmark_high']:.0%}")


if __name__ == "__main__":
    main()
