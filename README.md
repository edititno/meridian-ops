# Meridian Ops — Operations Analytics Dashboard

End-to-end operations analytics stack: ETL pipeline loading orders, inventory,
supplier, and costed BOM data into PostgreSQL, SQL-driven KPI analytics,
ML demand forecasting, and an optional LLM natural-language query layer.

**Live demo:** (add URL after deploy)

## Stack
- **Python** (pandas, scikit-learn, SQLAlchemy)
- **PostgreSQL** on cloud infrastructure (Railway) — SQL written portable/Snowflake-compatible
- **Streamlit + Plotly** dashboard
- Optional **LLM query layer** (Anthropic or OpenAI)

## What it demonstrates
| Capability | Where |
|---|---|
| ETL pipeline & data modeling | `src/etl.py`, `sql/schema.sql` |
| SQL analytics (CTEs, window-style aggregation) | `sql/analytics.sql` |
| Demand forecasting (seasonal-trend regression) | `src/forecast.py` |
| Executive KPI dashboards | `src/app.py` |
| Supplier performance & lead time analysis | Supplier tab |
| Costed BOMs & margin analytics | BOM tab |
| GenAI integration on operational data | Ask the Data tab |

## Run locally
```bash
pip install -r requirements.txt
python src/etl.py            # seeds local SQLite if no DATABASE_URL set
streamlit run src/app.py
```

## Deploy
1. Provision PostgreSQL (Railway) and set `DATABASE_URL`
2. `python src/etl.py` once against that database
3. Deploy to Streamlit Community Cloud pointing at `src/app.py`,
   with `DATABASE_URL` (and optionally an LLM API key) in app secrets
