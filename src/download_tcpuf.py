import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import requests
from config import RAW
H={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
# Anchored on __file__ via config.RAW so the script works from any cwd.
OUT=RAW/"tcpuf"; OUT.mkdir(parents=True,exist_ok=True)
YEARS={
 2022:"https://data.healthcare.gov/datafile/py2022/transparency_in_coverage_puf.xlsx",
 2023:"https://data.healthcare.gov/datafile/py2023/transparency_in_coverage_PUF.xlsx",
 2024:"https://data.healthcare.gov/datafile/py2024/transparency_in_coverage_PUF.xlsx",
 2025:"https://data.healthcare.gov/datafile/py2025/transparency_in_coverage_PUF.xlsx",
 2026:"https://data.healthcare.gov/datafile/py2026/transparency_in_coverage_PUF.xlsx",
}
for y,u in YEARS.items():
    p=OUT/f"tcpuf_py{y}.xlsx"
    if p.exists() and p.stat().st_size>10000:
        print(f"skip {y} ({p.stat().st_size:,}b)"); continue
    r=requests.get(u,headers=H,timeout=300)
    print(y,r.status_code,f"{len(r.content):,} bytes")
    if r.status_code==200: p.write_bytes(r.content)
