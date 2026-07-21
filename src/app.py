"""Meridian Ops: operations analytics dashboard.

Streamlit app: exec KPIs, demand forecasting, supplier performance,
inventory position, costed BOM margins, and an optional LLM query box.
"""
import os
import re
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from db import get_engine
from forecast import forecast_sku

st.set_page_config(page_title="Meridian Ops", layout="wide")

QUERIES_PATH = os.path.join(os.path.dirname(__file__), "..", "sql", "analytics.sql")


@st.cache_data(ttl=600)
def load_named_queries() -> dict:
    raw = open(QUERIES_PATH).read()
    blocks = re.split(r"-- name: (\w+)", raw)[1:]
    return {blocks[i]: blocks[i + 1].strip().rstrip(";") for i in range(0, len(blocks), 2)}


@st.cache_data(ttl=600)
def run_query(name: str) -> pd.DataFrame:
    q = load_named_queries()[name]
    return pd.read_sql(q, get_engine())


st.title("Meridian Ops")
st.caption("Operations analytics: Python + SQL stack: ETL to PostgreSQL, forecasting, and executive KPIs. Sample operational dataset.")

# ---- Exec KPI header ----
try:
    kpi = run_query("kpi_summary").iloc[0]
    c1, c2, c3 = st.columns(3)
    c1.metric("Orders (90d)", f"{int(kpi['orders_90d']):,}")
    c2.metric("Units shipped (90d)", f"{int(kpi['units_90d']):,}")
    c3.metric("Revenue (90d)", f"${int(kpi['revenue_90d']):,}")
except Exception as e:
    st.error(f"Database not reachable or not seeded. Run src/etl.py first. ({e})")
    st.stop()

tab_fc, tab_sup, tab_inv, tab_bom, tab_ask = st.tabs(
    ["Demand Forecast", "Supplier Performance", "Inventory", "Costed BOM & Margin", "Ask the Data"]
)

# ---- Demand forecasting ----
with tab_fc:
    demand = run_query("weekly_demand")
    demand["week"] = pd.to_datetime(demand["week"])
    sku = st.selectbox("Product", sorted(demand["sku"].unique()))
    hist = demand[demand["sku"] == sku][["week", "units"]]
    fc = forecast_sku(hist, horizon_weeks=12)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist["week"], y=hist["units"], name="Actual", mode="lines"))
    fig.add_trace(go.Scatter(x=fc["week"], y=fc["forecast"], name="Forecast", mode="lines",
                             line=dict(dash="dash")))
    fig.add_trace(go.Scatter(x=pd.concat([fc["week"], fc["week"][::-1]]),
                             y=pd.concat([fc["hi80"], fc["lo80"][::-1]]),
                             fill="toself", opacity=0.2, name="80% band", line=dict(width=0)))
    fig.update_layout(height=420, margin=dict(t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("12-week forecast from a seasonal-trend regression fit per SKU; band = ±1.28σ of residuals.")

# ---- Supplier performance ----
with tab_sup:
    sup = run_query("supplier_performance")
    left, right = st.columns([2, 3])
    with left:
        st.dataframe(sup, use_container_width=True, hide_index=True)
    with right:
        fig = px.bar(sup, x="supplier", y="on_time_pct", color="region",
                     labels={"on_time_pct": "On-time %"})
        fig.update_layout(height=380, margin=dict(t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)
    trend = run_query("lead_time_trend")
    fig2 = px.line(trend, x="month", y="avg_slip_days", markers=True,
                   labels={"avg_slip_days": "Avg schedule slip (days)"})
    fig2.update_layout(height=300, margin=dict(t=30, b=10))
    st.plotly_chart(fig2, use_container_width=True)

# ---- Inventory ----
with tab_inv:
    inv = run_query("inventory_position")
    st.dataframe(inv, use_container_width=True, hide_index=True)
    low = inv[inv["weeks_of_supply"].notna() & (inv["weeks_of_supply"] < 4)]
    if len(low):
        st.warning(f"Reorder risk: {', '.join(low['sku'])} below 4 weeks of supply.")

# ---- Costed BOM ----
with tab_bom:
    bom = run_query("costed_bom")
    st.dataframe(bom, use_container_width=True, hide_index=True)
    fig = px.bar(bom, x="sku", y=["material_cost", "unit_margin"],
                 labels={"value": "$ per unit"}, barmode="stack")
    fig.update_layout(height=380, margin=dict(t=30, b=10))
    st.plotly_chart(fig, use_container_width=True)

# ---- LLM natural language query (optional) ----
with tab_ask:
    st.write("Ask a question about the operational data in plain English.")
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        st.info("LLM querying is disabled (no API key configured). All analytics above run on pure SQL.")
    else:
        question = st.text_input("Question", placeholder="Which supplier causes the most schedule slip?")
        if "ask_count" not in st.session_state:
            st.session_state.ask_count = 0
        if question and st.session_state.ask_count >= 10:
            st.warning("Question limit reached for this session.")
        elif question and len(question) > 300:
            st.warning("Please keep questions under 300 characters.")
        elif question:
            st.session_state.ask_count += 1
            context = {name: run_query(name).head(25).to_csv(index=False)
                       for name in ["supplier_performance", "inventory_position", "costed_bom", "kpi_summary"]}
            prompt = (
                "You are an operations analyst. Using ONLY the CSV data below, answer the question "
                "concisely with specific numbers. If the data cannot answer it, say so.\n\n"
                + "\n\n".join(f"## {k}\n{v}" for k, v in context.items())
                + f"\n\nQuestion: {question}"
            )
            try:
                if os.environ.get("ANTHROPIC_API_KEY"):
                    import anthropic
                    client = anthropic.Anthropic()
                    msg = client.messages.create(
                        model="claude-haiku-4-5-20251001", max_tokens=500,
                        messages=[{"role": "user", "content": prompt}])
                    st.markdown(msg.content[0].text)
                else:
                    from openai import OpenAI
                    client = OpenAI()
                    resp = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}])
                    st.markdown(resp.choices[0].message.content)
            except Exception as e:
                st.error(f"LLM call failed: {e}")