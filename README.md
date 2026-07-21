# Meridian Ops — Operations Analytics Dashboard

End-to-end operations analytics stack: ETL pipeline loading orders, inventory,
supplier, and costed BOM data into PostgreSQL, SQL-driven KPI analytics,
ML demand forecasting, and an optional LLM natural-language query layer.

**Live demo:** https://meridian-ops-production.up.railway.app

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
Deployed on Railway: the Streamlit app and PostgreSQL run as linked services,
with auto-deploy from GitHub on every push to main.

1. Create a Railway project from this repo and add a PostgreSQL service
2. Reference `DATABASE_URL` from Postgres in the app's variables
3. Set the start command: `streamlit run src/app.py --server.port $PORT --server.address 0.0.0.0`
4. Run `python src/etl.py` once against the database to load data
5. Optional: set `ANTHROPIC_API_KEY` to enable the natural-language query tab
