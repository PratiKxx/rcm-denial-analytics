# Deployment

The dashboard deploys to Streamlit Community Cloud on the free tier.

---

## Why this works without the raw data

`app.py` reads only `data/processed/` (3.5 MB), which **is** committed. The 554 MB of
raw CMS source files are gitignored and are not needed at runtime — they are only
required to re-run the pipeline. So the deployed app is small and fast.

---

## 1. Push to GitHub

```bash
git init
git add .
git commit -m "Claims denial analytics and recovery model"
```

Create an empty **public** repo on GitHub named `rcm-denial-analytics`, then:

```bash
git remote add origin https://github.com/<your-username>/rcm-denial-analytics.git
git branch -M main
git push -u origin main
```

Confirm before pushing that `data/raw/` is excluded:

```bash
git status --short | grep "data/raw" || echo "raw data correctly excluded"
```

---

## 2. Deploy

**One-click link** — this pre-fills the repo, branch, and entry point:

https://share.streamlit.io/deploy?repository=PratiKxx/rcm-denial-analytics&branch=main&mainModule=app.py

Sign in with GitHub, confirm the pre-filled form, and press **Deploy**. First build
takes 2–3 minutes.

Manual equivalent, if the link changes: go to https://share.streamlit.io → **New app**
→ select `rcm-denial-analytics`, branch `main`, main file `app.py`.

You get a URL like `https://rcm-denial-analytics.streamlit.app`.

---

## 3. Custom URL

In the app's **Settings → General**, set a subdomain. Something short reads better on
a résumé — `claims-denial-analytics` or `denial-recovery-model`.

---

## Redeploy after changes

Streamlit Cloud auto-redeploys on push to `main`.

```bash
git add -A
git commit -m "<what changed>"
git push
```

If you change anything in `src/`, regenerate outputs and docs before pushing so the
deployed app and the generated documents stay in sync:

```bash
python run_pipeline.py --skip-download
python tests/test_uat.py
python src/generate_rtm.py
python src/generate_data_dictionary.py
```

---

## Building the Power BI file

`data/processed/star/` is import-ready.

1. Power BI Desktop → **Get Data → Text/CSV**, load all seven tables.
2. **Model view** → create the relationships listed at the top of `measures.dax`
   (all single-direction, many-to-one from fact to dimension).
3. Mark `dim_date` as a date table on `date_key`.
4. New table `_Measures`, paste the DAX definitions from `measures.dax`.
5. Build the pages: denial funnel, root cause breakdown, payer scatter, state map.

Roughly 90 minutes of work.

---

## Troubleshooting

**Module not found on Streamlit Cloud** — confirm `requirements.txt` is at the repo
root and lists the package.

**App can't find the parquet files** — confirm `data/processed/` was committed.
`.gitignore` excludes `data/raw/` and `data/interim/` only:

```bash
git ls-files data/processed | head
```

**App is slow on first load** — expected. `@st.cache_data` warms after the first
request.
