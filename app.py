import streamlit as st
import os

from dotenv import load_dotenv

import agent
from data_tools import ExcelAnalyzer


load_dotenv()


st.set_page_config(
    page_title="AI Excel Data Analyst",
    page_icon="📊",
    layout="wide"
)


st.title("📊 AI Excel/Data Analyst Agent")

st.write(
    "Upload an Excel or CSV file and ask questions about your data."
)


uploaded_file = st.file_uploader(
    "Upload your dataset",
    type=["xlsx", "xls", "csv"]
)


if uploaded_file:

    os.makedirs("data", exist_ok=True)

    file_path = os.path.join(
        "data",
        uploaded_file.name
    )

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    try:

        agent.analyzer = ExcelAnalyzer(file_path)

        st.success("Dataset loaded successfully!")

        df = agent.analyzer.df

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Rows",
            len(df)
        )

        col2.metric(
            "Columns",
            len(df.columns)
        )

        col3.metric(
            "Missing Values",
            int(df.isnull().sum().sum())
        )

        st.subheader("Dataset Preview")

        st.dataframe(
            df.head(20),
            use_container_width=True
        )

        st.divider()

        st.subheader("🤖 Ask your Data Analyst")

        question = st.chat_input(
            "Ask something about your dataset..."
        )

        if question:

            with st.chat_message("user"):
                st.write(question)

            with st.chat_message("assistant"):

                with st.spinner("Analyzing your data..."):

                    response = agent.ask_agent(question)

                    st.write(response)

    except Exception as e:

        st.error(
            f"Error loading dataset: {e}"
        )