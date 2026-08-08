"""
Canonical schema, denial taxonomy, and analysis constants.

Single source of truth for the source-to-target mapping documented in
docs/DATA_DICTIONARY.md. Every rename rule here has a matching row there.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"
FIGURES = ROOT / "figures"
DOCS = ROOT / "docs"

for _p in (RAW, INTERIM, PROCESSED, OUTPUTS, FIGURES):
    _p.mkdir(parents=True, exist_ok=True)

PLAN_YEARS = [2022, 2023, 2024, 2025, 2026]

# TC-PUF reports data from two plan years prior to the file's plan-year label.
# PY2026 file carries PY2024 experience. Confirmed in the CMS file disclaimer.
PY_TO_EXPERIENCE_YEAR = {y: y - 2 for y in PLAN_YEARS}

# ---------------------------------------------------------------------------
# Suppression markers. CMS uses these instead of nulls; treating them as 0
# would understate denominators and inflate every rate downstream.
# ---------------------------------------------------------------------------
SUPPRESSION_CODES = {
    "*": "not_available",          # data not available for this issuer/plan
    "**": "suppressed_small_cell",  # suppressed due to small cell size
    "***": "not_required",          # not required due to plan type
    "N/A": "not_applicable",        # issuer/plan new to the Exchange
    "NA": "not_applicable",
    "": "blank",
}

# ---------------------------------------------------------------------------
# Source-to-target mapping, by schema generation.
#   GEN1 (PY2022-PY2023): claims not split by network status
#   GEN2 (PY2024):        network split introduced; trailing-quote typo present
#   GEN3 (PY2025-PY2026): enrollment fields renamed, Exchange_Type added
# ---------------------------------------------------------------------------
SCHEMA_GENERATION = {2022: "GEN1", 2023: "GEN1", 2024: "GEN2", 2025: "GEN3", 2026: "GEN3"}

_COMMON = {
    "State": "state",
    "Issuer_Name": "issuer_name",
    "Issuer_ID": "issuer_id",
    "Plan_ID": "plan_id",
    "Plan_Type": "plan_type",
    "Metal_Level": "metal_level",
    "URL_Claims_Payment_Policies": "url_claims_policy",
    "Issuer_Internal_Appeals_Filed": "issuer_internal_appeals_filed",
    "Issuer_Number_Internal_Appeals_Overturned": "issuer_internal_appeals_overturned",
    "Issuer_External_Appeals_Filed": "issuer_external_appeals_filed",
    "Issuer_Number_External_Appeals_Overturned": "issuer_external_appeals_overturned",
    "Plan_Number_Claims_Denied_Referral_Required": "den_referral_required",
    "Plan_Number_Claims_Denied_Due_To_Out_Of_Network": "den_out_of_network",
    "Plan_Number_Claims_Denied_Services_Excluded": "den_service_excluded",
    "Plan_Number_Claims_Denied_Not_Medically_Necessary_Behavioral_Health_Only": "den_med_nec_behavioral",
    "Plan_Number_Claims_Denied_Due_To_Enrolle_Benefit_Limit_Reached": "den_benefit_limit",
    "Plan_Number_Claims_Denied_Due_To_Member_Not_Covered": "den_member_not_covered",
    "Plan_Number_Claims_Denied_Due_To_Investigational_Experimental_Cosmetic_Proceduce": "den_investigational",
    "Plan_Number_Claims_Denied_Due_To_Administrative_Reason": "den_administrative",
    "Plan_Number_Claims_Denied_Other": "den_other",
}

# GEN1/GEN2 spell the non-behavioral medical necessity column differently.
_MEDNEC_GEN12 = {
    "Plan_Number_Claims_Denied_Not_Medically_Necessary_Excl_Behavioral_Health": "den_med_nec_other",
}
_MEDNEC_GEN3 = {
    "Plan_Number_Claims_Denied_Not_Medically_Necessary_Excluding_Behavioral_Health": "den_med_nec_other",
}

COLUMN_MAP = {
    "GEN1": {
        **_COMMON, **_MEDNEC_GEN12,
        "SADP_Only?": "sadp_only",
        "QHP/SADP": "product_type",
        "Is_Issuer_New_to_Exchange? (Yes_or_No)": "issuer_new_to_exchange",
        # GEN1 reports totals only, with no in/out-of-network split.
        "Issuer_Claims_Received": "issuer_claims_received_total",
        "Issuer_Claims_Denials": "issuer_claims_denied_total",
        "Plan_Number_Claims_Received": "plan_claims_received_total",
        "Plan_Number_Claims_Denied": "plan_claims_denied_total",
        "Enrollment_Data": "avg_monthly_enrollment",
        "Disenrollment_Data": "avg_monthly_disenrollment",
    },
    "GEN2": {
        **_COMMON, **_MEDNEC_GEN12,
        "SADP_Only": "sadp_only",
        "QHP or SADP?": "product_type",
        "Is_Issuer_New_to_Exchange?(Yes_or_No)": "issuer_new_to_exchange",
        "New_or_Returning_Plan": "plan_new_or_returning",
        "Issuer_Claims_Received_In_Network": "issuer_claims_received_in",
        "Issuer_Claims_Received_Out_of_Network": "issuer_claims_received_out",
        "Issuer_Claims_Denied_In_Network": "issuer_claims_denied_in",
        # DEFECT DQ-003: PY2024 ships this header with a trailing double quote.
        'Issuer_Claims_Denied_Out_of_Network"': "issuer_claims_denied_out",
        "Issuer_Claims_Denied_Out_of_Network": "issuer_claims_denied_out",
        "Issuer_Claims_Resubmitted_In_Network": "issuer_claims_resubmitted_in",
        "Issuer_Claims_Resubmitted_Out_of_Network": "issuer_claims_resubmitted_out",
        "Plan_Number_Claims_Received_In_Network": "plan_claims_received_in",
        "Plan_Number_Claims_Received_Out_of_Network": "plan_claims_received_out",
        "Plan_Number_Claims_Denied_In_Network": "plan_claims_denied_in",
        "Plan_Number_Claims_Denied_Out_of_Network": "plan_claims_denied_out",
        "Plan_Number_Claims_Resubmitted_In_Network": "plan_claims_resubmitted_in",
        "Plan_Number_Claims_Resubmitted_Out_of_Network": "plan_claims_resubmitted_out",
        "Enrollment_Data": "avg_monthly_enrollment",
        "Disenrollment_Data": "avg_monthly_disenrollment",
    },
    "GEN3": {
        **_COMMON, **_MEDNEC_GEN3,
        "SADP_Only": "sadp_only",
        "QHP or SADP?": "product_type",
        "Is_Issuer_New_to_Exchange?(Yes_or_No)": "issuer_new_to_exchange",
        "Individual/SHOP": "market",
        "Exchange_Type": "exchange_type",
        "Issuer_Claims_Received_In_Network": "issuer_claims_received_in",
        "Issuer_Claims_Received_Out_of_Network": "issuer_claims_received_out",
        "Issuer_Claims_Denied_In_Network": "issuer_claims_denied_in",
        "Issuer_Claims_Denied_Out_of_Network": "issuer_claims_denied_out",
        "Issuer_Claims_Resubmitted_In_Network": "issuer_claims_resubmitted_in",
        "Issuer_Claims_Resubmitted_Out_of_Network": "issuer_claims_resubmitted_out",
        "Plan_Number_Claims_Received_In_Network": "plan_claims_received_in",
        "Plan_Number_Claims_Received_Out_of_Network": "plan_claims_received_out",
        "Plan_Number_Claims_Denied_In_Network": "plan_claims_denied_in",
        "Plan_Number_Claims_Denied_Out_of_Network": "plan_claims_denied_out",
        "Plan_Number_Claims_Resubmitted_In_Network": "plan_claims_resubmitted_in",
        "Plan_Number_Claims_Resubmitted_Out_of_Network": "plan_claims_resubmitted_out",
        "Average Monthly Enrollment": "avg_monthly_enrollment",
        "Average Monthly Disenrollment": "avg_monthly_disenrollment",
    },
}

DENIAL_REASON_COLS = [
    "den_referral_required", "den_out_of_network", "den_service_excluded",
    "den_med_nec_other", "den_med_nec_behavioral", "den_benefit_limit",
    "den_member_not_covered", "den_investigational", "den_administrative",
    "den_other",
]

# ---------------------------------------------------------------------------
# RCM root-cause taxonomy.
#
# Maps the payer-reported denial reason to where in the provider revenue cycle
# the defect originates, which is what determines who owns the fix. This is the
# analytical bridge from "payer denied it" to "our process caused it".
#
#   preventability: share of denials in this category a provider can prevent
#                   at source through process change (assumption, see BRD-014)
#   appealability:  share that are clinically/contractually worth appealing
#   effort_hours:   analyst/clinical hours per appeal (assumption, see BRD-015)
# ---------------------------------------------------------------------------
ROOT_CAUSE_TAXONOMY = {
    "den_referral_required": {
        "root_cause": "Front-End: Authorization & Referral",
        "owner": "Patient Access",
        "x12_carc_examples": "CARC 15, 197",
        "preventability": 0.85, "appealability": 0.55, "effort_hours": 1.0,
    },
    "den_out_of_network": {
        "root_cause": "Front-End: Eligibility & Network Verification",
        "owner": "Patient Access",
        "x12_carc_examples": "CARC 242, 243",
        "preventability": 0.70, "appealability": 0.30, "effort_hours": 1.5,
    },
    "den_member_not_covered": {
        "root_cause": "Front-End: Eligibility & Network Verification",
        "owner": "Patient Access",
        "x12_carc_examples": "CARC 27, 31",
        "preventability": 0.90, "appealability": 0.25, "effort_hours": 0.5,
    },
    "den_med_nec_other": {
        "root_cause": "Clinical: Medical Necessity",
        "owner": "Clinical Documentation Improvement",
        "x12_carc_examples": "CARC 50, 55",
        "preventability": 0.45, "appealability": 0.75, "effort_hours": 3.0,
    },
    "den_med_nec_behavioral": {
        "root_cause": "Clinical: Medical Necessity (Behavioral Health)",
        "owner": "Clinical Documentation Improvement",
        "x12_carc_examples": "CARC 50",
        "preventability": 0.40, "appealability": 0.80, "effort_hours": 3.5,
    },
    "den_investigational": {
        "root_cause": "Clinical: Coverage Policy",
        "owner": "Utilization Management",
        "x12_carc_examples": "CARC 55, 57",
        "preventability": 0.35, "appealability": 0.60, "effort_hours": 4.0,
    },
    "den_administrative": {
        "root_cause": "Mid-Cycle: Coding & Claim Submission",
        "owner": "HIM / Coding",
        "x12_carc_examples": "CARC 16, 4, 11",
        "preventability": 0.80, "appealability": 0.70, "effort_hours": 0.75,
    },
    "den_service_excluded": {
        "root_cause": "Benefit Design: Contractual Exclusion",
        "owner": "Contracting / Benefits",
        "x12_carc_examples": "CARC 96, 204",
        "preventability": 0.25, "appealability": 0.15, "effort_hours": 2.0,
    },
    "den_benefit_limit": {
        "root_cause": "Benefit Design: Benefit Maximum Reached",
        "owner": "Contracting / Benefits",
        "x12_carc_examples": "CARC 119, 35",
        "preventability": 0.30, "appealability": 0.20, "effort_hours": 1.0,
    },
    "den_other": {
        "root_cause": "Unclassified",
        "owner": "Revenue Integrity",
        "x12_carc_examples": "n/a",
        "preventability": 0.40, "appealability": 0.40, "effort_hours": 2.0,
    },
}

# ---------------------------------------------------------------------------
# Monetization assumptions. Every one of these is surfaced as a dashboard
# slider and stress-tested in outputs/sensitivity.csv. See docs/EXEC_MEMO.md.
# ---------------------------------------------------------------------------
def _load_derived_claim_value():
    """
    Read the claim value derived by src/derive_claim_value.py from CMS payment
    files. Falls back to the last committed derivation if the file is absent so
    the pipeline still runs, but the derivation is the intended source.
    """
    import json
    p = OUTPUTS / "claim_value.json"
    if p.exists():
        d = json.loads(p.read_text())
        return d["blended_commercial_allowed_per_claim"], d["low"], d["high"], True
    return 1336.32, 1002.0, 1737.0, False


_CV, _CV_LO, _CV_HI, _CV_LIVE = _load_derived_claim_value()

ASSUMPTIONS = {
    "avg_allowed_amount_per_claim": {
        "value": _CV, "low": _CV_LO, "high": _CV_HI,
        "source": "Derived in src/derive_claim_value.py from CMS DY2024 Inpatient "
                  "(DRG), Outpatient (C-APC), and Physician payment files, weighted "
                  "by a four-bucket claim mix and adjusted to commercial rates. "
                  f"{'Loaded live from outputs/claim_value.json.' if _CV_LIVE else 'Using committed fallback value.'}",
    },
    "appeal_cost_per_hour": {
        "value": 62.0, "low": 45.0, "high": 90.0,
        "source": "Blended fully-loaded hourly rate for a denials analyst plus "
                  "prorated clinical reviewer time.",
    },
    "collection_rate_on_overturn": {
        "value": 0.94, "low": 0.85, "high": 0.99,
        "source": "Share of overturned claim value actually collected after "
                  "secondary adjustments and patient responsibility.",
    },
    "resubmission_success_rate": {
        "value": 0.55, "low": 0.40, "high": 0.70,
        "source": "Share of resubmitted (reworked) claims that ultimately pay. "
                  "TC-PUF reports resubmission volume but not resubmission outcome, "
                  "so this is the one funnel stage that is assumed rather than observed.",
    },
    "rework_touch_cost": {
        "value": 25.0, "low": 12.0, "high": 45.0,
        "source": "Fully-loaded cost of one manual touch to rework and resubmit a "
                  "denied claim, excluding formal appeal handling.",
    },
    "denial_value_at_risk_share": {
        "value": 0.25, "low": 0.15, "high": 0.40,
        "source": "Share of a denied claim's allowed amount genuinely at risk. A "
                  "claim-level denial event in TC-PUF is not a total loss: many are "
                  "line-level, partial, duplicate, coordination-of-benefits routing, "
                  "or zero-dollar administrative denials. Calibrated so modelled "
                  "denial loss falls inside the published 3-5 percent of net patient "
                  "revenue band. See CALIBRATION in docs/EXEC_MEMO.md.",
    },
}

# Published benchmark the model is calibrated against. If modelled denial loss
# falls outside this band, the calibration check in analyze.py fails loudly.
CALIBRATION_BAND_PCT_OF_REVENUE = (0.03, 0.05)

# ---------------------------------------------------------------------------
# Reference provider profile.
#
# TC-PUF is payer-reported and national. A national dollar figure is too large to
# be decision-useful, so observed rates are scaled to one realistic provider
# organization. This is the unit a revenue cycle director actually manages.
# ---------------------------------------------------------------------------
PROVIDER_PROFILE = {
    "name": "Reference Regional Health System",
    "description": "420-bed non-profit acute care system with an employed physician "
                   "group, operating in a single state.",
    "annual_marketplace_claims": 184_000,
    "source": "Sized to a mid-market health system's annual commercial Exchange claim "
              "volume. Scale is a dashboard input; all findings are stated as rates "
              "so they re-scale to any volume.",
}

MIN_CLAIMS_FOR_RATE = 100  # rate suppression floor; below this, rates are unstable
MIN_APPEALS_FOR_RATE = 10  # overturn-rate floor
