import os
import io
import time
import streamlit as st

import config
import logger
import api
import database
import excel
import utils

from api import GeminiClassifier
from database import db_manager
from excel import (
    read_input_file,
    merge_classification_results,
    export_to_excel,
    create_sample_excel,
)
from utils import detect_email_columns

# Streamlit Page Settings & UI Theme Config
st.set_page_config(
    page_title="AI Customer Email Classifier",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling for Dashboard Header and Badges
st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #4F46E5;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #6B7280;
        margin-bottom: 1.5rem;
    }
    .status-card-ok {
        background-color: #ECFDF5;
        border: 1px solid #A7F3D0;
        color: #065F46;
        padding: 0.6rem 0.8rem;
        border-radius: 6px;
        font-size: 0.88rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    .status-card-err {
        background-color: #FEF2F2;
        border: 1px solid #FCA5A5;
        color: #991B1B;
        padding: 0.6rem 0.8rem;
        border-radius: 6px;
        font-size: 0.88rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_table(records: list, max_rows: int = 100) -> None:
    """Renders a modern, responsive HTML data table with styled urgency & sentiment badges."""
    if not records:
        st.info("No data records available to display.")
        return

    headers = list(records[0].keys())

    html = """
    <div style="overflow-x: auto; max-height: 450px; border: 1px solid #CBD5E1; border-radius: 8px; margin-bottom: 1rem;">
      <table style="width: 100%; border-collapse: collapse; font-family: system-ui, -apple-system, sans-serif; font-size: 0.88rem;">
        <thead>
          <tr style="background-color: #F1F5F9; text-align: left; position: sticky; top: 0; border-bottom: 2px solid #CBD5E1; z-index: 10;">
    """
    for h in headers:
        html += f'<th style="padding: 10px 14px; font-weight: 600; color: #1E293B; white-space: nowrap;">{h}</th>'
    html += "</tr></thead><tbody>"

    for idx, row in enumerate(records[:max_rows]):
        bg_color = "#FFFFFF" if idx % 2 == 0 else "#F8FAFC"
        html += f'<tr style="background-color: {bg_color}; border-bottom: 1px solid #E2E8F0;">'
        for h in headers:
            val = str(row.get(h, ""))
            val_lower = val.lower()

            # Format visual badges for urgency and sentiment
            if h.lower() == "urgency":
                if val_lower in ["high", "urgent"]:
                    val_html = f'<span style="background-color: #FEE2E2; color: #991B1B; padding: 3px 8px; border-radius: 4px; font-weight: 600;">{val}</span>'
                else:
                    val_html = f'<span style="background-color: #E0E7FF; color: #3730A3; padding: 3px 8px; border-radius: 4px; font-weight: 600;">{val}</span>'
            elif h.lower() == "sentiment":
                if val_lower == "positive":
                    val_html = f'<span style="background-color: #DCFCE7; color: #166534; padding: 3px 8px; border-radius: 4px; font-weight: 600;">{val}</span>'
                elif val_lower == "negative":
                    val_html = f'<span style="background-color: #FEE2E2; color: #991B1B; padding: 3px 8px; border-radius: 4px; font-weight: 600;">{val}</span>'
                else:
                    val_html = f'<span style="background-color: #F1F5F9; color: #475569; padding: 3px 8px; border-radius: 4px; font-weight: 600;">{val}</span>'
            else:
                val_html = val.replace("<", "&lt;").replace(">", "&gt;")

            html += f'<td style="padding: 10px 14px; color: #334155; vertical-align: top;">{val_html}</td>'
        html += "</tr>"

    html += "</tbody></table></div>"
    st.markdown(html, unsafe_allow_html=True)


def main():
    # Application Title & Header
    st.markdown('<div class="main-title">📧 AI Customer Email Classifier</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">Intelligent structured email classification powered by Google Gemini API & SQLite</div>',
        unsafe_allow_html=True,
    )

    # ------------------ SIDEBAR CONFIGURATION ------------------
    st.sidebar.header("⚙️ Configuration")

    # Instantiate Gemini API client
    classifier = GeminiClassifier()

    # Display Status Badge based on .env configuration
    if classifier.is_key_configured():
        st.sidebar.markdown(
            '<div class="status-card-ok">🟢 API Key: Configured in .env</div>',
            unsafe_allow_html=True,
        )
    else:
        st.sidebar.markdown(
            '<div class="status-card-err">🔴 API Key: Missing in .env file</div>',
            unsafe_allow_html=True,
        )
        st.sidebar.caption("Please paste your key inside the `.env` file in the project folder.")

    # Active Gemini Model Selection
    model_choice = st.sidebar.selectbox(
        "Gemini Model",
        options=[
            "gemini-flash-latest",
            "gemini-2.5-flash",
            "gemini-pro-latest",
            "Custom Model...",
        ],
        index=0,
        help="gemini-flash-latest is recommended for fast, accurate email classification.",
    )

    if model_choice == "Custom Model...":
        model_choice = st.sidebar.text_input("Enter Model Name", value="gemini-flash-latest")

    # Batch DB Insertion Toggle
    batch_db_save = st.sidebar.checkbox(
        "Batch Insert into Database",
        value=True,
        help="Saves email classification logs in batch to SQLite after processing.",
    )

    # Live Connection Test Button
    st.sidebar.markdown("---")
    if st.sidebar.button("🔌 Test API Connection"):
        if not classifier.is_key_configured():
            st.sidebar.error("GEMINI_API_KEY is missing. Please add your key to the `.env` file.")
        else:
            with st.sidebar.spinner(f"Testing live API connection with '{model_choice}'..."):
                classifier = GeminiClassifier()
                success, msg = classifier.test_connection(model_name=model_choice)
                if success:
                    st.sidebar.success(msg)
                else:
                    st.sidebar.error(f"Connection Failed:\n{msg}")

    # Sample File Downloader
    st.sidebar.markdown("---")
    st.sidebar.subheader("📁 Need Sample Data?")
    sample_file_path = config.Config.DATA_DIR / "sample_customer_emails.xlsx"
    if not sample_file_path.exists():
        create_sample_excel("sample_customer_emails.xlsx")

    if sample_file_path.exists():
        with open(sample_file_path, "rb") as f:
            st.sidebar.download_button(
                label="📥 Download Sample Excel",
                data=f,
                file_name="sample_customer_emails.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    # ------------------ MAIN TABBED INTERFACE ------------------
    tab1, tab2, tab3 = st.tabs(
        ["🚀 Classify Emails", "📜 SQLite Processed History", "📊 Analytics Dashboard"]
    )

    # ================= TAB 1: CLASSIFY EMAILS =================
    with tab1:
        st.subheader("Upload & Process Email Data")

        uploaded_file = st.file_uploader(
            "Upload Customer Emails file (Excel `.xlsx` or CSV `.csv`)",
            type=["xlsx", "csv"],
            help="File should contain email subject and body text columns.",
        )

        use_sample = st.checkbox("Use bundled sample emails dataset for testing")

        records, columns = [], []
        if uploaded_file:
            records, columns = read_input_file(uploaded_file)
        elif use_sample:
            records, columns = read_input_file(str(sample_file_path))
            st.info("Loaded bundled sample dataset (5 customer emails).")

        if records and columns:
            st.write(f"**Data Preview ({len(records)} rows):**")
            render_table(records[:5])

            auto_subj, auto_body = detect_email_columns(columns)

            c1, c2, c3 = st.columns(3)
            with c1:
                subj_col = st.selectbox(
                    "Select Subject Column",
                    options=columns,
                    index=columns.index(auto_subj) if auto_subj in columns else 0,
                )
            with c2:
                body_col = st.selectbox(
                    "Select Email Body Column",
                    options=columns,
                    index=columns.index(auto_body) if auto_body in columns else (1 if len(columns) > 1 else 0),
                )
            with c3:
                id_col = st.selectbox(
                    "Select Optional ID Column",
                    options=["None"] + columns,
                    index=0,
                )

            # Processing Trigger
            if st.button("✨ Run Classification Engine", type="primary"):
                if not classifier.is_key_configured():
                    st.error("❌ GEMINI_API_KEY is not configured! Open `.env` in the project folder and paste your key.")
                else:
                    classifier = GeminiClassifier()
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    results_list = []
                    db_records = []

                    total_rows = len(records)
                    start_time = time.time()

                    for idx, row in enumerate(records):
                        subj_text = str(row.get(subj_col, "")).strip()
                        body_text = str(row.get(body_col, "")).strip()
                        row_id = str(row.get(id_col, f"ROW-{idx+1}")) if id_col != "None" else f"ROW-{idx+1}"

                        status_text.text(f"Processing ({idx+1}/{total_rows}): '{subj_text[:40]}...'")

                        try:
                            # Call Live Gemini AI API
                            classification = classifier.classify_email(
                                subject=subj_text,
                                body=body_text,
                                model_name=model_choice,
                            )
                            res_dict = classification.model_dump()
                        except Exception as err:
                            logger.error(f"Error classifying row {idx+1}: {err}")
                            st.error(f"❌ Failed row {idx+1} ('{subj_text[:30]}'): {err}")
                            res_dict = {
                                "category": "Error",
                                "urgency": "Medium",
                                "sentiment": "Neutral",
                                "summary": f"Classification failed: {str(err)}",
                                "suggested_reply": "N/A",
                                "key_entities": [],
                            }

                        results_list.append(res_dict)

                        # Form record for SQLite DB
                        db_record = {
                            "email_id": row_id,
                            "subject": subj_text,
                            "body": body_text,
                            "category": res_dict.get("category"),
                            "urgency": res_dict.get("urgency"),
                            "sentiment": res_dict.get("sentiment"),
                            "summary": res_dict.get("summary"),
                            "suggested_reply": res_dict.get("suggested_reply"),
                            "key_entities": res_dict.get("key_entities"),
                        }
                        db_records.append(db_record)

                        if not batch_db_save:
                            db_manager.insert_record(db_record)

                        progress_bar.progress((idx + 1) / total_rows)

                    # Execute batch insert into SQLite database
                    if batch_db_save and db_records:
                        db_manager.batch_insert_records(db_records)

                    elapsed_time = round(time.time() - start_time, 2)
                    status_text.success(
                        f"✅ Completed classification of {total_rows} emails in {elapsed_time}s!"
                    )

                    # Merge results with input data & display
                    final_records = merge_classification_results(records, results_list)
                    st.write("### 🎯 Classification Results")
                    render_table(final_records)

                    # Export output Excel spreadsheet
                    output_file_path = export_to_excel(final_records)
                    if os.path.exists(output_file_path):
                        with open(output_file_path, "rb") as f:
                            st.download_button(
                                label="📥 Download Classified Excel File",
                                data=f,
                                file_name="classified_customer_emails.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            )

    # ================= TAB 2: SQLITE HISTORY =================
    with tab2:
        st.subheader("📜 Processed Email Database Logs (SQLite)")
        db_records = db_manager.get_all_records(limit=500)

        if not db_records:
            st.info("No email records found in SQLite database yet. Process emails in Tab 1!")
        else:
            st.write(f"Showing last **{len(db_records)}** stored records from `emails.db`:")
            render_table(db_records)

    # ================= TAB 3: ANALYTICS DASHBOARD =================
    with tab3:
        st.subheader("📊 Email Analytics & Insights")
        summary = db_manager.get_analytics_summary()

        m1, m2, m3 = st.columns(3)
        m1.metric("Total Emails Processed", summary["total_processed"])
        m2.metric(
            "Urgent / High Priority",
            summary["urgencies"].get("High", 0) + summary["urgencies"].get("Urgent", 0),
        )
        m3.metric("Unique Categories", len(summary["categories"]))

        st.markdown("---")
        col_a, col_b = st.columns(2)

        with col_a:
            st.write("#### 🏷️ Categories Breakdown")
            if summary["categories"]:
                st.json(summary["categories"])
            else:
                st.caption("No category records available yet.")

        with col_b:
            st.write("#### ⚡ Urgency Distribution")
            if summary["urgencies"]:
                st.json(summary["urgencies"])
            else:
                st.caption("No urgency records available yet.")


if __name__ == "__main__":
    main()
