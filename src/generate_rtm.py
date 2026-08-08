"""
Generate the requirements traceability matrix by parsing BRD.md and joining to
executed UAT results.

A hand-maintained RTM drifts out of sync with the build the first time a
requirement changes. This derives it, so a requirement with no test case or a
test case referencing a non-existent requirement is caught mechanically.

Output
    docs/RTM.csv
"""
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

REQ_ROW = re.compile(
    r"^\|\s*(BRD-\d+|NFR-\d+)\s*\|\s*(.+?)\s*\|\s*(Must|Should|Could|Won't)?\s*\|?\s*(.+?)\s*\|\s*$")


def parse_brd():
    rows, section = [], ""
    for line in (DOCS / "BRD.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("### 6.") or line.startswith("## 7."):
            section = line.lstrip("#").strip()
        m = REQ_ROW.match(line)
        if m:
            rid, text, prio, accept = m.groups()
            rows.append(dict(requirement_id=rid, section=section,
                             requirement=text.strip(),
                             priority=(prio or "Must").strip(),
                             acceptance_criteria=accept.strip()))
    return pd.DataFrame(rows).drop_duplicates(subset=["requirement_id"])


def parse_uat():
    p = DOCS / "UAT_RESULTS.csv"
    if not p.exists():
        raise SystemExit("Run tests/test_uat.py before generating the RTM.")
    u = pd.read_csv(p)
    rows = []
    for _, r in u.iterrows():
        for rid in [x.strip() for x in str(r.brd_ids).split(",")]:
            rows.append(dict(requirement_id=rid, test_case_id=r.test_case_id,
                             test_title=r.title, test_status=r.status,
                             test_evidence=r.actual))
    return pd.DataFrame(rows)


DESIGN = {
    "BRD-001": "src/download_tcpuf.py", "BRD-002": "src/config.py :: COLUMN_MAP",
    "BRD-003": "src/harmonize.py :: clean_numeric",
    "BRD-004": "src/harmonize.py :: build_issuer_panel",
    "BRD-005": "src/config.py :: MIN_CLAIMS_FOR_RATE",
    "BRD-006": "src/harmonize.py :: build_plan_panel",
    "BRD-007": "src/harmonize.py :: log_dq",
    "BRD-010": "src/config.py :: ROOT_CAUSE_TAXONOMY",
    "BRD-011": "src/config.py :: ROOT_CAUSE_TAXONOMY.owner",
    "BRD-012": "src/config.py :: ROOT_CAUSE_TAXONOMY.x12_carc_examples",
    "BRD-013": "src/analyze.py :: reason_mix",
    "BRD-014": "src/config.py :: ROOT_CAUSE_TAXONOMY.preventability",
    "BRD-015": "src/config.py :: ROOT_CAUSE_TAXONOMY.effort_hours",
    "BRD-016": "src/derive_claim_value.py",
    "BRD-017": "app.py :: Method tab",
    "BRD-018": "src/analyze.py :: recovery_model",
    "BRD-019": "src/analyze.py :: appeal_recommended",
    "BRD-020": "src/analyze.py :: prevention_value",
    "BRD-021": "app.py :: unclassified warning",
    "BRD-022": "src/analyze.py :: sensitivity",
    "BRD-023": "app.py :: sidebar sliders",
    "BRD-024": "src/analyze.py :: calibration_check",
    "BRD-025": "src/analyze.py :: issuer_scorecard",
    "BRD-026": "src/analyze.py :: appeal_target_score",
    "BRD-027": "src/analyze.py :: state_summary",
    "BRD-028": "src/analyze.py :: prioritize",
    "BRD-029": "src/star_schema.py",
    "BRD-030": "app.py :: claim volume input",
    "BRD-031": "app.py :: Provenance",
    "NFR-01": "run_pipeline.py", "NFR-02": "run_pipeline.py timing",
    "NFR-03": "run_pipeline.py", "NFR-04": "app.py :: st.cache_data",
    "NFR-05": "docs/DATA_DICTIONARY.md :: provenance",
    "NFR-06": "module docstrings",
}


def main():
    req = parse_brd()
    uat = parse_uat()
    rtm = req.merge(uat, on="requirement_id", how="left")
    rtm["design_component"] = rtm["requirement_id"].map(DESIGN).fillna("")
    rtm["test_case_id"] = rtm["test_case_id"].fillna("")
    rtm["test_status"] = rtm["test_status"].fillna("Not automated")
    rtm["verification_method"] = rtm["test_case_id"].apply(
        lambda x: "Automated UAT" if x else "Inspection")

    rtm = rtm[["requirement_id", "section", "requirement", "priority",
               "acceptance_criteria", "design_component", "verification_method",
               "test_case_id", "test_status", "test_evidence"]]
    rtm = rtm.sort_values("requirement_id")
    rtm.to_csv(DOCS / "RTM.csv", index=False)

    # Bidirectional coverage check.
    orphan_tests = sorted(set(uat.requirement_id) - set(req.requirement_id))
    untested = sorted(rtm[rtm.test_case_id == ""].requirement_id)

    print(f"requirements parsed : {len(req)}")
    print(f"RTM rows            : {len(rtm)}")
    print(f"covered by UAT      : {rtm[rtm.test_case_id != ''].requirement_id.nunique()}")
    print(f"verified by inspection: {len(untested)}  {untested}")
    if orphan_tests:
        print(f"WARNING orphan test references (no such requirement): {orphan_tests}")
    failed = rtm[rtm.test_status.isin(["FAIL", "ERROR"])]
    print(f"failing requirements: {len(failed)}")


if __name__ == "__main__":
    main()
