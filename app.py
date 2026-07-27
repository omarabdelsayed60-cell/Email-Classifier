import os
import io
import time
import streamlit as st
import pandas as pd
import plotly.express as px

import config
import api
import database
import excel
import utils

from logger import logger
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
    initial_sidebar_state="expanded",)

# Custom Styling for Dashboard Header and Badges
st.markdown(
    """
    <style>
    /* Global Page Font Scaling (+1 size larger across the board) */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 1.05rem !important;
    }

    .main-title {
        font-size: 2.4rem;
        font-weight: 800;
        color: #3730A3;
        margin-bottom: 0.3rem;
    }
    .sub-title {
        font-size: 1.15rem;
        color: #4B5563;
        margin-bottom: 1.8rem;
    }

    /* Sidebar Styling - Larger & High Contrast */
    section[data-testid="stSidebar"] {
        font-size: 1.08rem !important;
    }
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stTextInput label,
    section[data-testid="stSidebar"] .stCheckbox label,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] span {
        font-size: 1.05rem !important;
        font-weight: 700 !important;
        color: #F8FAFC !important;
    }


    /* Professional Button Styling for Run Classification Engine */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2563EB 0%, #1E40AF 100%) !important;
        color: #FFFFFF !important;
        font-size: 1.08rem !important;
        font-weight: 700 !important;
        padding: 0.65rem 1.6rem !important;
        border-radius: 8px !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(30, 64, 175, 0.3) !important;
        transition: all 0.2s ease-in-out !important;
    }
    div.stButton > button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 16px rgba(30, 64, 175, 0.4) !important;
        background: linear-gradient(135deg, #1D4ED8 0%, #172554 100%) !important;
    }

    /* Professional Dark Slate Button for Stop Analyzing */
    div.stButton > button[key="stop_btn"] {
        background-color: #475569 !important;
        color: #FFFFFF !important;
        font-size: 1.02rem !important;
        font-weight: 700 !important;
        padding: 0.6rem 1.4rem !important;
        border-radius: 8px !important;
        border: 1px solid #334155 !important;
        box-shadow: 0 2px 6px rgba(71, 85, 105, 0.25) !important;
        transition: all 0.2s ease-in-out !important;
    }
    div.stButton > button[key="stop_btn"]:hover {
        background-color: #334155 !important;
        box-shadow: 0 4px 10px rgba(51, 65, 85, 0.35) !important;
    }
    .status-card-err {
        background-color: #FEF2F2;
        border: 1px solid #FCA5A5;
        color: #991B1B;
        padding: 0.6rem 0.8rem;
        border-radius: 6px;
        font-size: 0.95rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,)



def render_table(records: list, max_rows: int = 100) -> None:
    """Renders a high-end, responsive enterprise data table with styled pill badges and crisp layout."""
    if not records:
        st.info("No data records available to display.")
        return

    headers = list(records[0].keys())

    html = """
    <style>
      .custom-table-wrapper {
          overflow-x: auto;
          max-height: 480px;
          border: 1px solid #E2E8F0;
          border-radius: 12px;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
          margin-bottom: 1.5rem;
          background-color: #FFFFFF;
      }
      .custom-table {
          width: 100%;
          border-collapse: separate;
          border-spacing: 0;
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          font-size: 0.88rem;
      }
      .custom-table th {
          background-color: #e1e6f2;
          color: #000000;
          font-weight: 700;
          font-size: 0.82rem;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          padding: 14px 16px;
          text-align: left;
          position: sticky;
          top: 0;
          z-index: 10;
          border-bottom: 2px solid #334155;
          white-space: nowrap;
      }
      .custom-table td {
          padding: 12px 16px;
          color: #334155;
          vertical-align: top;
          border-bottom: 1px solid #F1F5F9;
          line-height: 1.5;
      }
      .custom-table tr:nth-child(even) {
          background-color: #F8FAFC;
      }
      .custom-table tr:hover {
          background-color: #F1F5F9;
          transition: background-color 0.15s ease-in-out;
      }
      .badge-pill {
          display: inline-block;
          padding: 4px 10px;
          border-radius: 20px;
          font-weight: 700;
          font-size: 0.78rem;
          text-align: center;
          white-space: nowrap;
          box-shadow: 0 1px 2px rgba(0,0,0,0.05);
      }
    </style>
    <div class="custom-table-wrapper">
      <table class="custom-table">
        <thead>
          <tr>
    """
    for h in headers:
        html += f'<th>{h.replace("_", " ")}</th>'
    html += "</tr></thead><tbody>"

    for idx, row in enumerate(records[:max_rows]):
        html += "<tr>"
        for h in headers:
            val = str(row.get(h, ""))
            val_lower = val.lower()
            key_lower = h.lower()

            if key_lower == "urgency":
                if val_lower in ["high", "urgent"]:
                    val_html = f'<span class="badge-pill" style="background-color: #FEE2E2; color: #991B1B; border: 1px solid #FCA5A5;">🔥 {val}</span>'
                elif val_lower == "medium":
                    val_html = f'<span class="badge-pill" style="background-color: #FEF3C7; color: #92400E; border: 1px solid #FDE68A;">⚡ {val}</span>'
                else:
                    val_html = f'<span class="badge-pill" style="background-color: #E0E7FF; color: #3730A3; border: 1px solid #C7D2FE;">🔹 {val}</span>'
            elif key_lower == "sentiment":
                if val_lower == "positive":
                    val_html = f'<span class="badge-pill" style="background-color: #DCFCE7; color: #166534; border: 1px solid #86EFAC;">😊 {val}</span>'
                elif val_lower == "negative":
                    val_html = f'<span class="badge-pill" style="background-color: #FEE2E2; color: #991B1B; border: 1px solid #FCA5A5;">😟 {val}</span>'
                else:
                    val_html = f'<span class="badge-pill" style="background-color: #F1F5F9; color: #475569; border: 1px solid #CBD5E1;">😐 {val}</span>'
            elif key_lower == "category":
                val_html = f'<span class="badge-pill" style="background-color: #F3E8FF; color: #6B21A8; border: 1px solid #E9D5FF;">🏷️ {val}</span>'
            else:
                val_html = val.replace("<", "&lt;").replace(">", "&gt;")

            html += f"<td>{val_html}</td>"
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

    # Display Warning ONLY if API key is missing
    if not classifier.is_key_configured():
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
            "gemini-1.5-flash",
            "gemini-1.5-pro",
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

            # Processing Trigger Button
            run_button = st.button("✨ Run Classification Engine", type="primary")

            st.markdown("---")
            st.write(f"**Data Preview ({len(records)} rows):**")
            render_table(records[:5])

            if run_button:
                if not classifier.is_key_configured():
                    st.error("❌ GEMINI_API_KEY is not configured! Open `.env` in the project folder and paste your key.")
                else:
                    classifier = GeminiClassifier()
                    
                    prog_col, stop_col = st.columns([3, 1])
                    with prog_col:
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                    with stop_col:
                        stop_button = st.button("⏹️ Stop Analyzing", key="stop_btn")

                    results_list = []
                    db_records = []
                    total_rows = len(records)
                    start_time = time.time()
                    stopped_early = False

                    for idx, row in enumerate(records):
                        if stop_button:
                            stopped_early = True
                            break

                        subj_text = str(row.get(subj_col, "")).strip()
                        body_text = str(row.get(body_col, "")).strip()
                        row_id = str(row.get(id_col, f"ROW-{idx+1}")) if id_col != "None" else f"ROW-{idx+1}"

                        # 🔍 Deduplication Check: Re-use existing SQLite database record if ID matches
                        existing_record = db_manager.get_record_by_email_id(row_id)
                        if existing_record:
                            status_text.info(f"ℹ️ Reused existing database record for ID '{row_id}' ({idx+1}/{total_rows})")
                            res_dict = {
                                "category": existing_record.get("category", "General Inquiry"),
                                "urgency": existing_record.get("urgency", "Medium"),
                                "sentiment": existing_record.get("sentiment", "Neutral"),
                                "summary": existing_record.get("summary", ""),
                                "suggested_reply": existing_record.get("suggested_reply", ""),
                                "key_entities": [e.strip() for e in str(existing_record.get("key_entities", "")).split(",") if e.strip()],
                            }
                        else:
                            status_text.text(f"Processing ({idx+1}/{total_rows}): '{subj_text[:40]}...'")
                            try:
                                # Call Live Gemini AI API
                                classification = classifier.classify_email(
                                    subject=subj_text,
                                    body=body_text,
                                    model_name=model_choice,
                                )
                                res_dict = classification.model_dump()
                                # Pacing pause to respect Gemini Free Tier API rate limits (15 RPM)
                                time.sleep(2.0)

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

                        # Form record for SQLite DB (only save valid non-error records)
                        if res_dict.get("category") != "Error":
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

                            if not batch_db_save and not existing_record:
                                db_manager.insert_record(db_record)

                        progress_bar.progress((idx + 1) / total_rows)

                    # Execute batch insert into SQLite database for new valid records
                    if batch_db_save and db_records:
                        new_records = [r for r in db_records if not db_manager.get_record_by_email_id(r["email_id"])]
                        if new_records:
                            db_manager.batch_insert_records(new_records)

                    elapsed_time = round(time.time() - start_time, 2)
                    if stopped_early:
                        status_text.warning(
                            f"⏹️ Processing stopped by user. {len(results_list)} of {total_rows} emails processed and saved!"
                        )
                    else:
                        status_text.success(
                            f"✅ Completed classification of {total_rows} emails in {elapsed_time}s!"
                        )

                    # Merge results with input data & display preview
                    if results_list:
                        final_records = merge_classification_results(records[:len(results_list)], results_list)
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

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Emails Processed", summary["total_processed"])
        m2.metric(
            "Urgent / High Priority",
            summary["urgencies"].get("High", 0) + summary["urgencies"].get("Urgent", 0),
        )
        m3.metric("Unique Categories", len(summary["categories"]))
        m4.metric("Sentiments Analyzed", len(summary.get("sentiments", {})))

        st.markdown("---")

        if summary["total_processed"] == 0:
            st.info("💡 No analytics data available yet. Process some emails in the **🚀 Classify Emails** tab to view live charts!")
        else:
            col_a, col_b = st.columns(2)

            with col_a:
                st.markdown("##### 🏷️ Category Breakdown (Pie Chart)")
                if summary["categories"]:
                    df_cat = pd.DataFrame(
                        list(summary["categories"].items()),
                        columns=["Category", "Count"],
                    )
                    fig_cat = px.pie(
                        df_cat,
                        names="Category",
                        values="Count",
                        hole=0.4,
                        color_discrete_sequence=px.colors.qualitative.Set2,
                    )
                    fig_cat.update_traces(
                        textposition="outside",
                        textinfo="label+percent",
                        textfont=dict(size=14, family="Arial, sans-serif", color="#e1e6f2", weight="bold"),
                        marker=dict(line=dict(color="#FFFFFF", width=2)),
                    )
                    fig_cat.update_layout(
                        font=dict(size=14, family="Inter, sans-serif", color="#e1e6f2", weight="bold"),
                        legend=dict(font=dict(size=13, color="#e1e6f2", weight="bold")),
                        margin=dict(t=30, b=40, l=30, r=30),
                        height=380,
                    )
                    st.plotly_chart(fig_cat, width="stretch")
                else:
                    st.caption("No category records available yet.")

            with col_b:
                st.markdown("##### ⚡ Urgency Distribution (Bar Chart)")
                if summary["urgencies"]:
                    df_urg = pd.DataFrame(
                        list(summary["urgencies"].items()),
                        columns=["Urgency", "Count"],
                    )
                    color_map_urg = {
                        "High": "#EF4444",
                        "Urgent": "#DC2626",
                        "Medium": "#F59E0B",
                        "Low": "#3B82F6",
                    }
                    fig_urg = px.bar(
                        df_urg,
                        x="Urgency",
                        y="Count",
                        color="Urgency",
                        color_discrete_map=color_map_urg,
                        text="Count",
                    )
                    fig_urg.update_traces(
                        textfont=dict(size=15, family="Arial, sans-serif", color="#e1e6f2", weight="bold"),
                        textposition="outside",
                        marker=dict(line=dict(color="#FFFFFF", width=2)),
                    )
                    fig_urg.update_layout(
                        font=dict(size=14, family="Inter, sans-serif", color="#e1e6f2", weight="bold"),
                        xaxis=dict(
                            title_font=dict(size=15, color="#e1e6f2", weight="bold"),
                            tickfont=dict(size=14, color="#e1e6f2", weight="bold"),
                        ),
                        yaxis=dict(
                            title_font=dict(size=15, color="#e1e6f2", weight="bold"),
                            tickfont=dict(size=14, color="#e1e6f2", weight="bold"),
                        ),
                        margin=dict(t=30, b=30, l=30, r=30),
                        height=380,
                        showlegend=False,
                    )
                    st.plotly_chart(fig_urg, width="stretch")
                else:
                    st.caption("No urgency records available yet.")

            st.markdown("---")

            col_c, col_d = st.columns(2)

            with col_c:
                st.markdown("##### 😊 Sentiment Distribution (Donut Chart)")
                if summary.get("sentiments"):
                    df_sent = pd.DataFrame(
                        list(summary["sentiments"].items()),
                        columns=["Sentiment", "Count"],
                    )
                    color_map_sent = {
                        "Positive": "#10B981",
                        "Neutral": "#6B7280",
                        "Negative": "#EF4444",
                    }
                    fig_sent = px.pie(
                        df_sent,
                        names="Sentiment",
                        values="Count",
                        hole=0.4,
                        color="Sentiment",
                        color_discrete_map=color_map_sent,
                    )
                    fig_sent.update_traces(
                        textposition="outside",
                        textinfo="label+percent",
                        textfont=dict(size=14, family="Arial, sans-serif", color="#e1e6f2", weight="bold"),
                        marker=dict(line=dict(color="#FFFFFF", width=2)),
                    )
                    fig_sent.update_layout(
                        font=dict(size=14, family="Inter, sans-serif", color="#e1e6f2", weight="bold"),
                        legend=dict(font=dict(size=13, color="#e1e6f2", weight="bold")),
                        margin=dict(t=30, b=40, l=30, r=30),
                        height=380,
                    )
                    st.plotly_chart(fig_sent, width="stretch")
                else:
                    st.caption("No sentiment records available yet.")

            with col_d:
                with st.expander("📋 View Raw Analytics Data (JSON)"):
                    st.json(summary)


if __name__ == "__main__":
    main()
