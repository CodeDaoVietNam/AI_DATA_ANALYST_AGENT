import os
import requests
import streamlit as st
import pandas as pd

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(
    page_title="AI Data Analyst Agent",
    page_icon="📊",
    layout="wide"
)

st.title("📊 AI Data Analyst Agent")
st.caption("Upload CSV → EDA → Insights → Chat with your data")

if "dataset_id" not in st.session_state:
    st.session_state.dataset_id = None

uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])

if uploaded_file is not None:
    with st.spinner("Uploading file..."):
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")}
        response = requests.post(f"{BACKEND_URL}/upload", files=files)

    if response.status_code == 200:
        data = response.json()
        st.session_state.dataset_id = data["dataset_id"]
        st.success(f"Uploaded {data['filename']} with {data['rows']} rows and {data['columns']} columns.")
    else:
        st.error(response.text)

if st.session_state.dataset_id:
    dataset_id = st.session_state.dataset_id

    st.subheader("Dataset Summary")
    summary_response = requests.get(f"{BACKEND_URL}/summary/{dataset_id}")

    if summary_response.status_code == 200:
        summary = summary_response.json()

        col1, col2, col3 = st.columns(3)
        col1.metric("Rows", summary["shape"]["rows"])
        col2.metric("Columns", summary["shape"]["columns"])
        col3.metric("Duplicate Rows", summary["duplicate_rows"])

        st.write("### Column Types")
        st.json(summary["column_types"])

        st.write("### Missing Values")
        missing_df = pd.DataFrame({
            "column": list(summary["missing_values"].keys()),
            "missing_count": list(summary["missing_values"].values()),
            "missing_percent": [summary["missing_percent"][c] for c in summary["missing_values"].keys()]
        })
        st.dataframe(missing_df, use_container_width=True)

        st.write("### Recommended Analysis")
        for rec in summary["recommendations"]:
            st.info(rec)

    st.subheader("Ecommerce Insights")
    ecommerce_overview_response = requests.get(f"{BACKEND_URL}/ecommerce/overview/{dataset_id}")

    if ecommerce_overview_response.status_code == 200:
        ecommerce_data = ecommerce_overview_response.json()
        overview = ecommerce_data["overview"]
        data_quality = ecommerce_data["data_quality"]

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Revenue", f"{overview['total_revenue']:,.0f}")
        col2.metric("Unique Orders", f"{overview['unique_orders']:,}")
        col3.metric("Cancel Rate", f"{overview['cancel_rate'] * 100:.2f}%")
        col4.metric("Missing Amount", f"{overview['missing_amount_rows']:,}")

        st.caption(f"Date range: {overview['date_min']} → {overview['date_max']}")

        if data_quality.get("warnings"):
            with st.expander("Data quality warnings"):
                for warning in data_quality["warnings"]:
                    st.warning(warning)

        category_response = requests.get(f"{BACKEND_URL}/ecommerce/revenue-by-category/{dataset_id}")
        if category_response.status_code == 200:
            category_items = category_response.json()["items"]
            category_df = pd.DataFrame(category_items)
            if not category_df.empty:
                st.write("### Revenue by Category")
                st.dataframe(category_df, use_container_width=True)
                st.bar_chart(category_df.set_index("category")["revenue"])

        month_response = requests.get(f"{BACKEND_URL}/ecommerce/revenue-by-month/{dataset_id}")
        if month_response.status_code == 200:
            month_items = month_response.json()["items"]
            month_df = pd.DataFrame(month_items)
            if not month_df.empty:
                st.write("### Revenue by Month")
                st.line_chart(month_df.set_index("order_month")["revenue"])
    else:
        st.info("Ecommerce-specific insights are available for Amazon Sales style datasets.")

    st.subheader("Chat with Dataset")
    question = st.text_input("Ask a question, for example: Dataset có bao nhiêu dòng? Cột nào missing nhiều nhất?")

    if st.button("Ask") and question:
        chat_response = requests.post(
            f"{BACKEND_URL}/chat",
            json={"dataset_id": dataset_id, "question": question}
        )

        if chat_response.status_code == 200:
            result = chat_response.json()
            st.write("### Answer")
            st.write(result["answer"])

            if result.get("data") is not None:
                st.write("### Data")
                st.json(result["data"])
        else:
            st.error(chat_response.text)

    st.subheader("Export Report")
    if st.button("Generate Markdown Report"):
        report_response = requests.get(f"{BACKEND_URL}/report/{dataset_id}")
        if report_response.status_code == 200:
            report = report_response.json()["report_markdown"]
            st.download_button(
                label="Download report.md",
                data=report,
                file_name="eda_report.md",
                mime="text/markdown"
            )
            st.markdown(report)
        else:
            st.error(report_response.text)
