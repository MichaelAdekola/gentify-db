import streamlit as st
import re
from utils.db import DuckDBClient
from utils.llm import get_llm
from agents.sql_agent import build_sql_chain
from langchain.chains import create_sql_query_chain   


def fmt_num(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f} M"
    if n >= 1_000:
        return f"{n/1_000:.1f} K"
    return f"{n:,}"


st.set_page_config(page_title="Gentify-DB", layout="wide")
st.title("Gentify-DB – NL → SQL demo")

# --- load CSVs once --------------------------------------------------------
TABLE_MAP = {
    "sales":          "sample_data/sales.csv",
    "products":       "sample_data/products.csv",
    "time_dimension": "sample_data/time_dimension.csv",
    "order_items":    "sample_data/order_items.csv",
    "orders":         "sample_data/orders.csv",
    "customers":      "sample_data/customers.csv",
}

@st.cache_resource(show_spinner="Loading CSVs into DuckDB…")
def init_db():
    db = DuckDBClient()
    db.load_many(TABLE_MAP)        # runs only once per server start
    return db

db     = init_db()                 # cached instance
sql_db = db.get_sql_database()

# build a lightweight stats dict for the Explorer sidebar
stats = {}
for t in TABLE_MAP:
    rows = db.run_sql(f"SELECT COUNT(*) AS r FROM {t}").iloc[0, 0]
    cols = db.run_sql(f"PRAGMA table_info('{t}')").shape[0]
    stats[t] = (rows, cols)

if st.sidebar.button("🔄 Reload CSVs from disk"):
    init_db.clear()        # clear the cache
    st.experimental_rerun()

with st.sidebar.expander("🕓 Query History"):
    for q in st.session_state.get("history", []):
        # show first line truncated to 40 chars
        label = q.split("\n")[0][:40] + ("…" if len(q) > 40 else "")
        if st.button(label, key=f"hist_{hash(q)}"):
            st.session_state.latest_sql = q      # load into the editor
            st.session_state["sql_editor"] = q   # sync textarea
            st.experimental_rerun()
# ───────────────────────────────── MAIN LAYOUT ────────────────────────────
# 3 equal columns → Explorer | SQL Editor | LLM Copilot
exp_col, edit_col, copilot_col = st.columns([1.1, 2.4, 1.2], gap="large")

# -------- Database Object Explorer (left) ---------------------------------
with exp_col:
    st.markdown("### 📂 Explorer")
    for tbl, (r, c) in stats.items():
        with st.expander(f"**{tbl}**"):
            # show row / col counts as tidy metrics
            m1, m2 = st.columns(2)
            m1.metric("Rows", fmt_num(r))
            m2.metric("Cols", c)

            st.divider()  

            # list columns
            cols_df = db.run_sql(f"PRAGMA table_info('{tbl}')")
            for _, row in cols_df.iterrows():
                st.markdown(f"- `{row['name']}` · *{row['type']}*")


# -------- SQL Editor (middle) --------------------------------------------
with edit_col:
    st.markdown("### 💻 SQL Editor")
    # pre-fill with latest generated SQL if available
    default_sql = st.session_state.get("latest_sql", "")
    sql_editor = st.text_area(
        "Write or edit query:",
        value=default_sql,
        height=380,
        key="sql_editor",
        placeholder="SELECT …"
    )
    run_clicked = st.button("🟢 Run Query", key="run_query_button")

# -------- LLM Copilot (right) --------------------------------------------
with copilot_col:
    st.markdown("### 🤖 LLM Copilot")
    user_q = st.text_input(
        "Ask in plain English",
        placeholder="e.g. Show top 10 customers by revenue"
    )
    if st.button("✨ Generate SQL", key="gen_sql_button") and user_q:
        llm = get_llm(temperature=0)
        chain = build_sql_chain(llm, sql_db)
        with st.spinner("Thinking…"):
            raw_sql = chain.invoke({"question": user_q})
        # LangChain may return str or dict
        sql_text = raw_sql["result"].strip() if isinstance(raw_sql, dict) else str(raw_sql).strip()
        st.session_state.latest_sql = sql_text     # seed editor next time
        st.code(sql_text, language="sql")

# -------- Execute & show results (below the 3-column block) --------------
if run_clicked:
    import re, json
    sql_to_run = sql_editor.strip()
    # scrub fences / “sql ” prefix
    fence_pattern = r"^```(?:sql)?|```$"
    sql_to_run = re.sub(fence_pattern, "", sql_to_run, flags=re.I | re.M).strip()
    if sql_to_run.lower().startswith("sql "):
        sql_to_run = sql_to_run[4:].lstrip()

    with st.spinner("Executing…"):
        try:
            df = db.run_sql(sql_to_run)
        except Exception as e:
            st.error(f"SQL error: {e}")
        else:
            st.success(f"{len(df):,} rows • {df.shape[1]} columns")

            # store successful query in history (max 5)
            hist = st.session_state.setdefault("history", [])
            if "SELECT" in sql_to_run.upper():
                hist.insert(0, sql_to_run.strip())
                st.session_state.history = hist[:5]

            with st.container(border=True):      # replace tab block with this container
                tab_tbl, tab_json = st.tabs(["Table", "JSON"])
                with tab_tbl:
                    st.dataframe(df, use_container_width=True)
                with tab_json:
                    st.text(json.dumps(df.head(50).to_dict("records"), indent=2))



# ===========================================================================

# st.info("🚧 MVP scaffolding in progress…")


# put once at bottom of app.py
st.markdown("""
<style>
/* Title padding + letter-spacing */
h1 { padding-top: .5rem; letter-spacing: .05em; }

/* Expander header */
[data-testid="stExpander"] > summary {
    font-weight: 600; font-size: 0.9rem;
}

/* Containers & text areas */
div[data-testid="stVerticalBlock"] > div {
    border-radius: 8px;
    background-color: var(--secondary-background-color);
    padding: 1.2rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}

/* Dataframe striping */
tbody tr:nth-child(even) {
    background-color: rgba(255,255,255,0.02);
}
</style>
""", unsafe_allow_html=True)
