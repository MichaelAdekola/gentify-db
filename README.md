# Gentify-DB — NL → SQL Streamlit MVP

Gentify-DB is a single-page Streamlit app that lets you explore local CSV files
with natural-language questions.  
Behind the scenes it converts plain English to DuckDB-compatible SQL via
Google Gemini (LangChain), executes the query, and shows the results in a table.

---

## Features

| Capability | Notes |
|------------|-------|
| **CSV ingestion** | Loads any CSVs placed in `sample_data/` on start-up. |
| **Database** | DuckDB, persisted to `gentify.duckdb`. |
| **NL → SQL** | Gemini-Pro via LangChain, schema-aware prompt. |
| **SQL editor** | Generated query is editable before execution. |
| **Query history** | Keeps the last five successful SQL statements. |
| **Explorer** | Sidebar shows tables, row/column counts, and column types. |
| **Tabs** | Table and raw JSON views (chart tab to be added). |

---

## Quick start (local)

```bash
# Clone & enter
git clone https://github.com/<your-username>/gentify-db.git
cd gentify-db

# Create venv
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Add your Gemini API key
echo 'GEMINI_API_KEY="YOUR_KEY"' > .streamlit/secrets.toml

# Run
streamlit run app.py