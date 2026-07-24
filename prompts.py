from typing import List
from pydantic import BaseModel, Field


class EmailClassification(BaseModel):
    """Pydantic model defining the structured schema for Gemini classification output."""

    category: str = Field(
        description="Category of the email (e.g., Technical Support, Billing & Invoices, Sales / Lead, Feature Request, Spam / Irrelevant, General Inquiry)"
    )
    urgency: str = Field(
        description="Urgency level of the request: Low, Medium, High, or Urgent"
    )
    sentiment: str = Field(
        description="Customer sentiment: Positive, Neutral, or Negative"
    )
    summary: str = Field(
        description="Concise 1-sentence summary of the customer's email"
    )
    suggested_reply: str = Field(
        description="A polite, professional initial response draft tailored to the email content"
    )
    key_entities: List[str] = Field(
        default_factory=list,
        description="Extracted key details such as product names, account IDs, error codes, or invoice numbers",
    )


SYSTEM_PROMPT = """You are an expert AI Customer Support Email Classifier.
Your job is to accurately analyze customer support emails and classify them into structured data.

Analyze the given email subject and body carefully, then provide:
1. Category: Choose the most accurate category.
2. Urgency: Assess priority (Low, Medium, High, Urgent).
3. Sentiment: Identify emotional tone (Positive, Neutral, Negative).
4. Summary: Provide a 1-sentence summary.
5. Suggested Reply: Write a helpful, professional reply draft.
6. Key Entities: Extract relevant account numbers, product names, dates, or error codes.
"""


def build_user_prompt(subject: str, body: str) -> str:
    """Formats the user prompt with email subject and body."""
    return f"""Please classify the following customer email:

--- EMAIL START ---
Subject: {subject or 'N/A'}
Body:
{body or 'N/A'}
--- EMAIL END ---
"""
