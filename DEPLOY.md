# Deployment

The dashboard runs on Streamlit Community Cloud (free tier) at
**https://claims-denial-analytics.streamlit.app/**, deployed from `main` in this repo.

---

## Why the deploy is small

`app.py` reads only `data/processed/` and `outputs/` — about 3.7 MB, all committed. The
554 MB of raw CMS source files are gitignored and aren't needed at runtime; they're only
required to re-run the pipeline from scratch.

I verified this by hiding `data/raw/` entirely and re-running the app's full load path
before the first push, rather than finding out on the server.

---

## Redeploying

Streamlit Cloud auto-redeploys on every push to `main`.

```bash
git add -A
git commit -m "<what changed>"
git push
```

Anything that touches `src/` needs the outputs and generated docs rebuilt first, or the
deployed app and the committed documents drift apart:

```bash
python run_pipeline.py --skip-download
python tests/test_uat.py
python src/generate_rtm.py
python src/generate_data_dictionary.py
```

---

## Deploying a fresh copy

If this repo is ever forked or redeployed from scratch:

1. https://share.streamlit.io → **New app** → this repo, branch `main`, main file `app.py`.
   The pre-filled equivalent is
   `share.streamlit.io/deploy?repository=<owner>/rcm-denial-analytics&branch=main&mainModule=app.py`.
2. First build takes 2–3 minutes.
3. **Settings → Sharing** → set viewer access to public. This is easy to miss; a newly
   deployed app can default to requiring a Streamlit login, which makes the link useless
   to anyone who isn't signed in. Verify with:

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://claims-denial-analytics.streamlit.app/
```

`200` means public. `303` means it is redirecting to the auth gate and is still private.

4. **Settings → General** sets the subdomain.

---

## Environment pins

- `runtime.txt` pins Python 3.12. Without it, Cloud picks its own interpreter and every
  unbounded `>=` resolves against an unknown version.
- `requirements.txt` floors Streamlit at **1.49**, not lower. `app.py` passes
  `width="stretch"` to `st.plotly_chart` and `st.dataframe`, which is the
  post-deprecation layout API — earlier versions expect an int there and raise
  `TypeError` on every chart.
- `scipy` and `scikit-learn` are deliberately absent. Nothing imports them, and together
  they add roughly 159 MB to every cold build.

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

**Link asks for a Streamlit login** — the app is private. Settings → Sharing → public.

**Module not found on Cloud** — confirm `requirements.txt` is at the repo root and lists
the package.

**App can't find the parquet files** — confirm `data/processed/` was committed.
`.gitignore` excludes `data/raw/` and `data/interim/` only:

```bash
git ls-files data/processed
```

**TypeError on chart render** — the resolved Streamlit version is below 1.49. See the
environment pins above.

**Slow first load** — expected. `@st.cache_data` warms after the first request.
