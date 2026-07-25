import json
import time
from typing import Optional, Tuple
from google import genai
from google.genai import types
from google.genai.errors import APIError


from config import Config
from logger import logger
from prompts import EmailClassification, SYSTEM_PROMPT, build_user_prompt
from utils import create_retry_decorator


class GeminiClassifier:
    """Clean, production-ready Google Gemini API Client.
    
    Connects to Google Gemini AI over the internet, sends customer email text,
    and returns structured Pydantic classification outputs (Category, Urgency, Sentiment, Reply).
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initializes client reading GEMINI_API_KEY from environment (.env)."""
        raw_key = api_key or Config.get_gemini_api_key() or ""
        self.api_key = raw_key.strip().strip('"').strip("'")
        self.client = None

        if self.is_key_configured():
            self._init_client()

    def is_key_configured(self) -> bool:
        """Returns True if a valid API key is present in .env."""
        return bool(self.api_key and self.api_key != "your_gemini_api_key_here")

    def _init_client(self) -> None:
        """Initializes the official Google GenAI Client SDK."""
        if not self.is_key_configured():
            self.client = None
            return

        try:
            self.client = genai.Client(api_key=self.api_key)
            logger.info("Live Gemini API Client initialized successfully.")
        except Exception as err:
            logger.error(f"Failed to initialize Gemini Client: {err}")
            self.client = None

    @create_retry_decorator(max_attempts=3, min_seconds=2, max_seconds=10)
    def classify_email(
        self, subject: str, body: str, model_name: str = "gemini-flash-latest"
    ) -> EmailClassification:
        """Classifies email subject & body into structured Pydantic schema using Gemini API."""
        if not self.is_key_configured():
            raise ValueError(
                "Gemini API Key is missing! Please paste your key into the .env file."
            )


        if not self.client:
            self.client = genai.Client(api_key=self.api_key)

        # 2. Format user prompt and resolve model mapping
        user_prompt = build_user_prompt(subject=subject, body=body)
        raw_model = model_name.strip().replace("models/", "")
        model_map = {
            "gemini-2.5-flash": "gemini-1.5-flash",
            "gemini-pro-latest": "gemini-1.5-pro",
        }
        target_model = model_map.get(raw_model, raw_model)


        # 3. Call Google Gemini API with structured JSON output config
        try:
            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=EmailClassification,
                temperature=0.1,
            )

            response = self.client.models.generate_content(
                model=target_model, contents=user_prompt, config=config
            )

            # Return parsed EmailClassification object directly
            if hasattr(response, "parsed") and isinstance(response.parsed, EmailClassification):
                return response.parsed

            if response.text:
                return EmailClassification.model_validate_json(response.text)

            raise ValueError("API call succeeded but response text was empty.")

        except APIError as api_err:
            logger.error(f"Google Gemini API Error on model '{target_model}': {api_err}")
            err_str = str(api_err)

            if "400" in err_str or "API_KEY_INVALID" in err_str:
                raise ValueError("Invalid Gemini API Key! Please verify your key in the .env file.")
            elif "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                # Automatic rate limit handling: wait 6 seconds and retry up to 3 times
                for retry_attempt in range(1, 4):
                    logger.warning(f"Rate limit hit (429). Pausing 6s before retry {retry_attempt}/3...")
                    time.sleep(6)
                    try:
                        resp = self.client.models.generate_content(
                            model=target_model,
                            contents=user_prompt,
                            config=types.GenerateContentConfig(
                                system_instruction=SYSTEM_PROMPT,
                                response_mime_type="application/json",
                                response_schema=EmailClassification,
                                temperature=0.2,
                            ),
                        )
                        if resp.text:
                            return EmailClassification.model_validate_json(resp.text)
                    except Exception as retry_err:
                        logger.warning(f"Retry attempt {retry_attempt} failed: {retry_err}")
                        continue
                raise ValueError("Quota Rate Limit Exceeded (429)! Google's free tier rate limit was reached. Please wait 15–30 seconds before running again.")
            elif "404" in err_str or "not supported" in err_str.lower():
                logger.info(f"Model '{target_model}' not supported. Falling back to 'gemini-flash-latest'...")
                try:
                    resp_fb = self.client.models.generate_content(
                        model="gemini-flash-latest", contents=user_prompt, config=config
                    )
                    if resp_fb.text:
                        return EmailClassification.model_validate_json(resp_fb.text)
                except Exception as fb_err:
                    raise ValueError(f"Model '{target_model}' is not supported on your project. Use 'gemini-flash-latest'.")
            else:
                raise ValueError(f"Google API Error: {err_str}")



        except Exception as err:
            logger.error(f"Error classifying email on model '{target_model}': {err}")
            raise ValueError(f"Classification Error: {str(err)}")

    def test_connection(self, model_name: str = "gemini-flash-latest") -> Tuple[bool, str]:
        """Tests live API connection. Returns (success_bool, status_message)."""
        if not self.is_key_configured():
            return False, "GEMINI_API_KEY is not configured in .env file."

        try:
            result = self.classify_email(
                subject="Test connection ping",
                body="Hello, this is a test ping to verify Gemini API connection.",
                model_name=model_name,
            )
            if result and result.category:
                return True, f"API Connection Verified! Gemini AI is online (Category: {result.category})."
            return False, "API connected but output was empty."
        except Exception as err:
            logger.error(f"Gemini API connection test failed: {err}")
            return False, str(err)
