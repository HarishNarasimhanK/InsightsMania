from dotenv import load_dotenv
load_dotenv()

import os
import sqlite3
from typing import List, Tuple
import streamlit as st
import google.generativeai as gai 

gai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


## Loading the model
model = gai.GenerativeModel('gemma-3-27b-it')

def get_sql_query(query: str) -> str:
    """
    This function takes a natural language query as input and returns the corresponding SQL query.
    """
    prompt = f"""
    You are a highly skilled Marketing Analytics Assistant.

    Your job is to translate natural language business questions from marketing analysts into optimized SQL queries that retrieve actionable insights from a SQLite database.

    📊 The insights may involve:
    - Retrieving existing metrics like ROAS, CTR, CPC, CPA
    - Grouping data by platform, campaign, hour, or ad type
    - Filtering by date, platform, segment, or SKU
    - Generating derived metrics using basic formulas, such as:
        - ROAS = revenue / spend
        - CTR = (clicks / impressions) * 100
        - CPC = spend / clicks
        - CPA = spend / conversions
        - CPM = (spend / impressions) * 1000

    You must ONLY use fields and datatypes from the schema below and derive metrics using them. NEVER assume the existence of any field not listed.

    🗂 Table schema:

    CREATE TABLE customer (
        customer_id VARCHAR(20),
        platform VARCHAR(20),
        segment VARCHAR(20),
        SKU VARCHAR(50),
        hour INT,
        date DATE,
        ROAS FLOAT,
        CTR FLOAT,
        CPC FLOAT,
        CPM FLOAT,
        CPA FLOAT,
        impressions INT,
        clicks FLOAT,
        conversions FLOAT,
        spend FLOAT,
        revenue FLOAT,
        ad_name VARCHAR(100),
        ad_type VARCHAR(20),
        campaign_id VARCHAR(50)
    );

    📌 Guidelines:
    - Use **only** fields in the schema.
    - Return **only** a valid SQLite SQL query in the plain text format without any ``` or quotations.
    - If an insight can be computed from existing fields (e.g., custom ROI or cost efficiency), derive it correctly.
    - NEVER hallucinate table names or column names.
    - String and date values must be wrapped in single quotes.
    - Use `AS` to name computed columns clearly (e.g., `spend / conversions AS CPA`).
    - NEVER return anything other than the SQL query.
    - More importantly, if the query is invalid, return "INVALID QUERY".
    - If the query is valid but does not return any results, return "NO RESULTS".
    - If the query is valid and returns results, return the SQL query.
    🗣 Natural Language Request:
    "{query}"

💡  SQL Insight Output (only the SQL query):
    """
    response = model.generate_content([prompt, query])
    return response.text

def get_sql_results(query: str) -> List[Tuple]:
    """
    This function takes a SQL query as input and returns the corresponding results.
    """
    conn = sqlite3.connect('customer.db')
    cursor = conn.cursor()
    results = cursor.execute(query)
    rows = []   
    for row in results:
        rows.append(row)
    conn.close()
    return rows

def generate_insights(user_query : str, sql_query : str, results : str) -> str:
    """
    This function takes a SQL output as input and returns the corresponding insights.
    """
    prompt = f"""
    You are a senior marketing analyst assistant.

    Your role is to interpret the output of SQL queries run on advertising data. The result represents marketing KPIs (such as ROAS, CTR, CPC, CPA, spend, revenue, conversions, impressions) from the `customer` table of a SQLite database.

    Your task:
    - Analyze the tuple of results given to you.
    - Provide clear, concise, and actionable **marketing insights** in plain English.
    - Focus on what the numbers *mean* — e.g., which platform performed best, any efficiency issues, anomalies, or optimization opportunities.

    DO:
    - Highlight top-performing platforms, campaigns, or ad types.
    - Mention underperformers or efficiency concerns (e.g., high CPA or low ROAS).
    - Suggest what action a marketer might consider next (e.g., scale, pause, test creatives).
    - Mention derived metrics like conversion rate, ROAS improvements, etc., if possible.

    DON’T:
    - Repeat raw numbers unless it's meaningful.
    - Include SQL or technical explanations.
    - Hallucinate metrics not present in the result.

    Here is the user's query based on which the below SQL output has been generated:
    {user_query}
    and the sql query prepared by the LLM by taking the semantic context of the user's query:
    {sql_query}
    Here is the result of the SQL query:
    {results}
    Please write your marketing insight based on this result:
    """
    insight_response = model.generate_content([prompt])
    return insight_response.text

def main():
    st.set_page_config(page_title="InsightsMania", layout="centered")
    st.title("🎯 InsightsMania – Marketing Insights Generator")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_input = st.chat_input("Ask your marketing question here...")
    if user_input:
        # Store user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            # Step 1: Get SQL query
            sql_query = get_sql_query(user_input)
            if sql_query == "INVALID QUERY":
                st.error("Invalid SQL query. Please try again.")
            elif sql_query == "NO RESULTS":
                st.warning("No results found for this query.")
            else:
                st.markdown("**Generated SQL Query:**")
                st.code(sql_query, language="sql")

                # Step 2: Run SQL query and show results
                results = get_sql_results(sql_query)
                if not results:
                    st.warning("No data returned for this query.")
                else:
                    st.markdown("**SQL Output:**")
                    st.dataframe(results)
                    insight_response = generate_insights(user_input,sql_query, results)
                    st.markdown("💡**Insight:**")
                    st.success(insight_response)

                # Store assistant message
                st.session_state.messages.append({"role": "assistant", "content": insight_response if results else "No data to generate insights."})

if __name__ == "__main__":
    main()