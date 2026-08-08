"""
Stage 01c - Derive average allowed amount per claim from CMS payment data.

Sensitivity analysis identified allowed-amount-per-claim as the single most
load-bearing assumption in the recovery model, so it is derived from published
CMS payment files rather than asserted.

Derivation chain, each step sourced:

  1. Medicare allowed amount per unit, by care setting   [CMS, observed]
       inpatient   : Avg_Tot_Pymt_Amt per discharge, discharge-weighted
       outpatient  : Avg_Mdcr_Alowd_Amt per APC service, service-weighted
       professional: Tot_Mdcr_Alowd_Amt / Tot_Srvcs, national totals
  2. Units per claim, by setting                          [assumption]
  3. Claim mix by setting                                 [assumption]
  4. Commercial-to-Medicare price multiplier              [assumption]

Steps 2-4 are declared here with bounds and flow into outputs/sensitivity.csv.
Step 1 is observed and is not adjustable.

Output
    outputs/claim_value_derivation.csv
    outputs/claim_value.json
"""
import json

import pandas as pd

from config import OUTPUTS, RAW

PAY = RAW / "cms_payments"

# ---------------------------------------------------------------------------
# IMPORTANT SCOPE CORRECTION (see DQ-010 in outputs/dq_log.csv).
#
# The CMS outpatient file covers Comprehensive APCs only: 72 procedural APC
# groups (observation, musculoskeletal, endoscopy, intraocular, endovascular),
# 68 of which carry a priced row, averaging $5,123 per service. These are the
# highest-acuity outpatient encounters, not outpatient generally. Routine
# hospital outpatient volume
# (laboratory, imaging, clinic, therapy) is billed as HCPCS line items at a
# small fraction of that amount and is absent from this file.
#
# Treating the C-APC average as "the" outpatient value overstates blended claim
# value roughly tenfold. Outpatient is therefore split into two buckets: the
# procedural bucket priced from observed C-APC data, and an ancillary bucket
# priced from the professional per-line rate with a facility uplift.
# ---------------------------------------------------------------------------

# Units per claim.
UNITS_PER_CLAIM = {
    "inpatient": 1.0,            # one discharge per claim by definition
    "outpatient_procedural": 1.4,  # C-APC services per procedural claim
    "outpatient_ancillary": 3.0,   # HCPCS lines per ancillary claim
    "professional": 2.3,           # service lines per professional claim
}

# Claim mix by COUNT for an acute care system with an employed physician group.
# Inpatient is a small share of claim volume and the largest share of dollars.
CLAIM_MIX = {
    "inpatient": 0.020,
    "outpatient_procedural": 0.015,
    "outpatient_ancillary": 0.300,
    "professional": 0.665,
}

# Commercial payers reimburse well above Medicare, most steeply for facility
# services. Applied because TC-PUF covers commercial Exchange plans.
COMMERCIAL_TO_MEDICARE = {
    "inpatient": 2.10,
    "outpatient_procedural": 2.60,
    "outpatient_ancillary": 2.60,
    "professional": 1.40,
}

# Hospital outpatient ancillary services carry a facility fee above the
# professional fee schedule for the same HCPCS code.
FACILITY_UPLIFT_ANCILLARY = 1.9


def medicare_unit_values():
    """Volume-weighted Medicare allowed amount per unit, by setting. Observed."""
    out = {}

    inp = pd.read_csv(PAY / "inpatient_drg_dy24.csv",
                      usecols=["Tot_Dschrgs", "Avg_Tot_Pymt_Amt"])
    inp = inp.dropna()
    w = inp["Tot_Dschrgs"]
    out["inpatient"] = {
        "value": float((inp["Avg_Tot_Pymt_Amt"] * w).sum() / w.sum()),
        "unit": "discharge", "n_rows": int(len(inp)), "total_units": float(w.sum()),
        "field": "Avg_Tot_Pymt_Amt weighted by Tot_Dschrgs",
        "file": "MUP_INP_RY26_P03_V10_DY24_PrvSvc.CSV",
    }

    outp = pd.read_csv(PAY / "outpatient_apc_dy24.csv",
                       usecols=["APC_Cd", "CAPC_Srvcs", "Avg_Mdcr_Alowd_Amt"])
    outp = outp.dropna()
    w = outp["CAPC_Srvcs"]
    out["outpatient_procedural"] = {
        "value": float((outp["Avg_Mdcr_Alowd_Amt"] * w).sum() / w.sum()),
        "unit": "C-APC service", "n_rows": int(len(outp)), "total_units": float(w.sum()),
        "field": "Avg_Mdcr_Alowd_Amt weighted by CAPC_Srvcs",
        "file": "MUP_OUT_RY26_P04_V10_DY24_Prov_Svc.csv",
        "n_apc_groups": int(outp["APC_Cd"].nunique()),
        "scope_note": f"Comprehensive APCs only: {outp['APC_Cd'].nunique()} procedural "
                      f"APC groups carry a priced row (72 appear in the file; 4 have no "
                      f"allowed amount). Not representative of routine outpatient volume.",
    }

    tot_srv = tot_alw = 0.0
    n = 0
    for chunk in pd.read_csv(PAY / "physician_provider_dy24.csv",
                             usecols=["Tot_Srvcs", "Tot_Mdcr_Alowd_Amt"],
                             chunksize=400_000):
        chunk = chunk.dropna()
        tot_srv += float(chunk["Tot_Srvcs"].sum())
        tot_alw += float(chunk["Tot_Mdcr_Alowd_Amt"].sum())
        n += len(chunk)
    prof_per_line = tot_alw / tot_srv
    out["professional"] = {
        "value": prof_per_line, "unit": "service line", "n_rows": n,
        "total_units": tot_srv,
        "field": "sum(Tot_Mdcr_Alowd_Amt) / sum(Tot_Srvcs)",
        "file": "MUP_PHY_R26_P05_V10_D24_Prov.csv",
        "scope_note": "National totals across all rendering providers.",
    }
    # Routine hospital outpatient is HCPCS line-item billing, priced off the
    # professional per-line rate with a facility uplift. No CMS file publishes
    # routine outpatient line values directly, so this bucket is derived.
    out["outpatient_ancillary"] = {
        "value": prof_per_line * FACILITY_UPLIFT_ANCILLARY, "unit": "HCPCS line",
        "n_rows": n, "total_units": tot_srv,
        "field": f"professional per-line rate x {FACILITY_UPLIFT_ANCILLARY} facility uplift",
        "file": "derived from MUP_PHY_R26_P05_V10_D24_Prov.csv",
        "scope_note": "Derived, not directly observed. Covers lab, imaging, clinic, "
                      "and therapy volume absent from the C-APC file.",
    }
    return out


def main():
    units = medicare_unit_values()
    rows = []
    for setting in CLAIM_MIX:
        spec = units[setting]
        mcare_claim = spec["value"] * UNITS_PER_CLAIM[setting]
        comm_claim = mcare_claim * COMMERCIAL_TO_MEDICARE[setting]
        rows.append(dict(
            setting=setting, source_file=spec["file"], source_field=spec["field"],
            scope_note=spec.get("scope_note", ""),
            source_rows=spec["n_rows"], observed_units=spec["total_units"],
            medicare_allowed_per_unit=spec["value"], unit=spec["unit"],
            units_per_claim=UNITS_PER_CLAIM[setting],
            medicare_allowed_per_claim=mcare_claim,
            commercial_multiplier=COMMERCIAL_TO_MEDICARE[setting],
            commercial_allowed_per_claim=comm_claim,
            claim_mix_share=CLAIM_MIX[setting],
            weighted_contribution=comm_claim * CLAIM_MIX[setting]))

    df = pd.DataFrame(rows)
    blended = float(df["weighted_contribution"].sum())
    df.loc[len(df)] = {"setting": "BLENDED", "commercial_allowed_per_claim": blended,
                       "claim_mix_share": 1.0, "weighted_contribution": blended}
    df.to_csv(OUTPUTS / "claim_value_derivation.csv", index=False)

    # Bounds: vary the commercial multiplier within plausible ranges.
    low = sum(units[s]["value"] * UNITS_PER_CLAIM[s] * (COMMERCIAL_TO_MEDICARE[s] * 0.75)
              * CLAIM_MIX[s] for s in CLAIM_MIX)
    high = sum(units[s]["value"] * UNITS_PER_CLAIM[s] * (COMMERCIAL_TO_MEDICARE[s] * 1.30)
               * CLAIM_MIX[s] for s in CLAIM_MIX)

    payload = {
        "blended_commercial_allowed_per_claim": round(blended, 2),
        "low": round(low, 2), "high": round(high, 2),
        "medicare_unit_values": {k: round(v["value"], 2) for k, v in units.items()},
        "units_per_claim": UNITS_PER_CLAIM,
        "claim_mix": CLAIM_MIX,
        "commercial_to_medicare": COMMERCIAL_TO_MEDICARE,
        "observed_source_rows": {k: v["n_rows"] for k, v in units.items()},
        # outpatient_ancillary is derived from the physician file rather than read
        # from a fourth source, so summing observed_source_rows double-counts it.
        # This is the honest distinct total to cite.
        "distinct_source_rows": int(sum(
            v["n_rows"] for k, v in units.items() if k != "outpatient_ancillary")),
        "distinct_source_files": 3,
        "facility_uplift_ancillary": FACILITY_UPLIFT_ANCILLARY,
        "note": "Step 1 observed from CMS DY2024 payment files. Units per claim, "
                "claim mix, commercial multiplier, and the ancillary facility uplift "
                "are assumptions with bounds. See DQ-010 for the C-APC scope correction.",
    }
    (OUTPUTS / "claim_value.json").write_text(json.dumps(payload, indent=2))

    # Append this stage's data quality finding to the shared log. Run order is
    # enforced by run_pipeline.py: harmonize writes the log, this appends to it.
    dq_path = OUTPUTS / "dq_log.csv"
    finding = pd.DataFrame([dict(
        dq_id="DQ-010", severity="Critical", plan_year="n/a",
        field="MUP_OUT Avg_Mdcr_Alowd_Amt (scope)",
        finding=f"The CMS outpatient file covers Comprehensive APCs only "
                f"({units['outpatient_procedural']['n_rows']:,} priced rows across "
                f"{units['outpatient_procedural']['n_apc_groups']} procedural "
                f"APC groups, averaging "
                f"${units['outpatient_procedural']['value']:,.0f} per service). Routine "
                f"outpatient volume (lab, imaging, clinic, therapy) is absent. Using this "
                f"as the outpatient average overstates blended claim value roughly tenfold.",
        treatment="Outpatient split into a procedural bucket priced from observed C-APC "
                  "data and an ancillary bucket derived from the professional per-line "
                  "rate with a facility uplift",
        rows_affected=units["outpatient_procedural"]["n_rows"])])
    if dq_path.exists():
        existing = pd.read_csv(dq_path)
        existing = existing[existing["dq_id"] != "DQ-010"]
        pd.concat([finding, existing], ignore_index=True).to_csv(dq_path, index=False)
    else:
        finding.to_csv(dq_path, index=False)

    print("Medicare allowed per unit (DY2024):")
    for k in CLAIM_MIX:
        v = units[k]
        print(f"  {k:22s} ${v['value']:>10,.2f} per {v['unit']:<14s} "
              f"({v['n_rows']:,} rows)")
    print("\nCommercial allowed per claim (derived):")
    for _, r in df[df.setting != "BLENDED"].iterrows():
        print(f"  {r['setting']:22s} ${r['commercial_allowed_per_claim']:>10,.2f}"
              f"   mix {r['claim_mix_share']:>5.1%}"
              f"   contributes ${r['weighted_contribution']:>8,.2f}")
    print(f"\n  {'BLENDED':22s} ${blended:>10,.2f} per claim   "
          f"(range ${low:,.0f} - ${high:,.0f})")


if __name__ == "__main__":
    main()
