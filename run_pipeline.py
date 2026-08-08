"""
End-to-end pipeline. Run order matters: harmonize writes the data quality log,
derive_claim_value appends to it and produces the value that config feeds to
analyze, and star_schema reads the harmonized panels.

    python run_pipeline.py           full run
    python run_pipeline.py --skip-download    reuse files already in data/raw
"""
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = str(ROOT / ".venv" / "Scripts" / "python.exe")
if not Path(PY).exists():
    PY = sys.executable

STAGES = [
    ("Download TC-PUF", "src/download_tcpuf.py", True),
    ("Download CMS payment files", "src/download_cms_payments.py", True),
    ("Harmonize panel", "src/harmonize.py", False),
    ("Derive claim value", "src/derive_claim_value.py", False),
    ("Analyze", "src/analyze.py", False),
    ("Build star schema", "src/star_schema.py", False),
]


def main():
    skip_dl = "--skip-download" in sys.argv
    failures = []
    for i, (name, script, is_download) in enumerate(STAGES, 1):
        if skip_dl and is_download:
            print(f"[{i}/{len(STAGES)}] {name} — skipped")
            continue
        print(f"\n[{i}/{len(STAGES)}] {name}")
        print("-" * 70)
        t0 = time.time()
        r = subprocess.run([PY, script], cwd=ROOT)
        if r.returncode != 0:
            failures.append(name)
            print(f"FAILED after {time.time()-t0:.1f}s")
            break
        print(f"({time.time()-t0:.1f}s)")

    print("\n" + "=" * 70)
    if failures:
        print(f"PIPELINE FAILED at: {', '.join(failures)}")
        sys.exit(1)
    print("PIPELINE OK")
    print("\nNext:  streamlit run app.py")


if __name__ == "__main__":
    main()
