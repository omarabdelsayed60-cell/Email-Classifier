# 🗺️ AI Customer Email Classifier — Business Process Map Chart

![Process Map Flowchart Chart](screenshots/classic_process_map_chart.png)

---

## 📌 Standard Process Map Diagram

```text
  ┌────────────────────────┐
  │  1. START: Upload File │ (Excel .xlsx / .csv input)
  └───────────┬────────────┘
              │
              ▼
  ┌────────────────────────┐
  │ 2. Column Auto-Detect  │ (Identify Email ID, Subject, & Body)
  └───────────┬────────────┘
              │
              ▼
  ┌────────────────────────┐
  │  3. Gemini AI Analysis │ (Extract Category, Urgency, Sentiment,
  └───────────┬────────────┘  Summary & Suggested Reply via Pydantic)
              │
              ▼
  ┌────────────────────────┐
  │ 4. Database Storage    │ (Insert structured record into SQLite emails.db)
  └───────────┬────────────┘
              │
              ▼
  ┌────────────────────────┐
  │ 5. Excel Export        │ (Merge results & save to output/classified_emails.xlsx)
  └───────────┬────────────┘
              │
              ▼
  ┌────────────────────────┐
  │  6. END: Download File │ (Interactive Streamlit Dashboard download)
  └────────────────────────┘
```

---

## 🔄 Detailed Flowchart Diagram

```mermaid
graph TD
    classDef start fill:#4F46E5,stroke:#312E81,color:#fff,font-weight:bold
    classDef process fill:#0EA5E9,stroke:#075985,color:#fff,font-weight:bold
    classDef ai fill:#8B5CF6,stroke:#5B21B6,color:#fff,font-weight:bold
    classDef db fill:#10B981,stroke:#065F46,color:#fff,font-weight:bold
    classDef export fill:#F59E0B,stroke:#92400E,color:#fff,font-weight:bold

    S([Step 1: Upload Excel/CSV File]):::start --> P1[Step 2: Auto-Detect Subject & Body Columns]:::process
    P1 --> P2{Valid Columns Found?}:::process
    P2 -->|Yes| P3[Step 3: Call Gemini AI API for Email Batch]:::ai
    P2 -->|No| E1[Prompt User to Select Columns Manually]:::process
    E1 --> P3
    P3 --> P4[Step 4: Validate Structured Output with Pydantic]:::ai
    P4 --> P5[Step 5: Store Record in SQLite Database]:::db
    P5 --> P6[Step 6: Merge & Write to output/classified_emails.xlsx]:::export
    P6 --> FIN([Step 7: Download Final Excel Report]):::start
```
