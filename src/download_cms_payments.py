"""Stage 01b - Download CMS Medicare payment files used to derive claim value."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import requests
from config import RAW
H={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
# Anchored on __file__ via config.RAW so the script works from any cwd.
OUT=RAW/"cms_payments"; OUT.mkdir(parents=True,exist_ok=True)
FILES={
 "inpatient_drg_dy24.csv":"https://data.cms.gov/sites/default/files/2026-04/828defb5-c9e6-4442-8c1b-f27bc0799daf/MUP_INP_RY26_P03_V10_DY24_PrvSvc.CSV",
 "outpatient_apc_dy24.csv":"https://data.cms.gov/sites/default/files/2026-06/794975f5-e335-4cbf-8e87-982c834a9639/MUP_OUT_RY26_P04_V10_DY24_Prov_Svc.csv",
 "physician_provider_dy24.csv":"https://data.cms.gov/sites/default/files/2026-05/7323ba02-52e7-4a86-b2ce-ad210c25d9aa/MUP_PHY_R26_P05_V10_D24_Prov.csv",
}
for name,url in FILES.items():
    p=OUT/name
    if p.exists() and p.stat().st_size>100000:
        print(f"skip {name} ({p.stat().st_size/1e6:.1f} MB)"); continue
    with requests.get(url,headers=H,timeout=1800,stream=True) as r:
        r.raise_for_status()
        n=0
        with open(p,"wb") as f:
            for chunk in r.iter_content(1<<20):
                f.write(chunk); n+=len(chunk)
    print(f"{name}: {n/1e6:.1f} MB")
