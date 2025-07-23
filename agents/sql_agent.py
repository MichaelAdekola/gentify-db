"""
agents/sql_agent.py
Build a simple LangChain that injects the DuckDB schema
into the system prompt so Gemini can write accurate SQL.
"""

from langchain.prompts import ChatPromptTemplate
from langchain_community.utilities import SQLDatabase
from langchain.schema import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI


def get_schema(sql_db: SQLDatabase, max_chars: int = 4_000) -> str:
    """
    Return the full CREATE TABLE definitions for every table,
    truncated to `max_chars` so we don’t blow the context window.
    """
    schema = sql_db.get_table_info()
    return schema[:max_chars]


def build_sql_chain(llm: ChatGoogleGenerativeAI, sql_db: SQLDatabase):
    schema = get_schema(sql_db)

    system_msg = (
        "You are an expert data analyst writing DuckDB-compatible SQL.\n"
        "Return **only** a single valid SQL statement - no explanations, no ``` fences, no “sql ” prefix.\n"
        "Only use the tables/columns listed below. …"
        "Only use the tables and columns listed below.\n"
        "If a question can't be answered with this data, respond with "
        "'NO_VALID_SQL'.\n\n"
        f"### Database schema\n{schema}"
    )

    prompt = ChatPromptTemplate.from_messages(
        [("system", system_msg), ("user", "{question}")]
    )

    # Prompt → LLM → plain-text SQL string
    return prompt | llm | StrOutputParser()
