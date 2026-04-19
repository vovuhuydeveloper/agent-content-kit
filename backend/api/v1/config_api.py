"""
Config API — Manage API keys and Telegram settings.
"""

import logging
import os

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("api.config")

router = APIRouter(prefix="/config", tags=["Configuration"])


class KeysRequest(BaseModel):
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""
    pexels_api_key: str = ""
    elevenlabs_api_key: str = ""
    llm_provider: str = ""  # openai | claude | gemini
    # OAuth credentials
    youtube_client_id: str = ""
    youtube_client_secret: str = ""
    tiktok_client_key: str = ""
    tiktok_client_secret: str = ""
    facebook_app_id: str = ""
    facebook_app_secret: str = ""
    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""


class ValidateRequest(BaseModel):
    service: str
    key: str


class TelegramTestRequest(BaseModel):
    token: str
    chat_id: str


def _mask(key: str) -> str:
    if len(key) <= 8:
        return "****"
    return key[:4] + "****" + key[-4:]


@router.get("/keys", summary="Get saved keys (masked)")
def get_keys():
    return {
        "openai_api_key": _mask(os.environ.get("OPENAI_API_KEY", "")),
        "anthropic_api_key": _mask(os.environ.get("ANTHROPIC_API_KEY", "")),
        "google_api_key": _mask(os.environ.get("GOOGLE_API_KEY", "")),
        "pexels_api_key": _mask(os.environ.get("PEXELS_API_KEY", "")),
        "elevenlabs_api_key": _mask(os.environ.get("ELEVENLABS_API_KEY", "")),
        "telegram_bot_token": os.environ.get("TELEGRAM_BOT_TOKEN", ""),  # Not masked — user's own bot
        "telegram_chat_id": os.environ.get("TELEGRAM_CHAT_ID", ""),
        "llm_provider": os.environ.get("LLM_PROVIDER", "openai"),
    }


@router.post("/keys", summary="Save API keys")
def save_keys(data: KeysRequest):
    """Save keys to environment (runtime only — use .env for persistence)"""
    updated = []
    if data.openai_api_key:
        os.environ["OPENAI_API_KEY"] = data.openai_api_key
        updated.append("openai")
    if data.anthropic_api_key:
        os.environ["ANTHROPIC_API_KEY"] = data.anthropic_api_key
        updated.append("anthropic")
    if data.google_api_key:
        os.environ["GOOGLE_API_KEY"] = data.google_api_key
        updated.append("google")
    if data.pexels_api_key:
        os.environ["PEXELS_API_KEY"] = data.pexels_api_key
        updated.append("pexels")
    if data.elevenlabs_api_key:
        os.environ["ELEVENLABS_API_KEY"] = data.elevenlabs_api_key
        updated.append("elevenlabs")
    if data.llm_provider:
        os.environ["LLM_PROVIDER"] = data.llm_provider
        # Reset LLM manager to pick up new provider
        from backend.core.llm_manager import reset_llm_manager
        reset_llm_manager()
        updated.append("llm_provider")

    # OAuth credentials
    oauth_fields = {
        "YOUTUBE_CLIENT_ID": data.youtube_client_id,
        "YOUTUBE_CLIENT_SECRET": data.youtube_client_secret,
        "TIKTOK_CLIENT_KEY": data.tiktok_client_key,
        "TIKTOK_CLIENT_SECRET": data.tiktok_client_secret,
        "FACEBOOK_APP_ID": data.facebook_app_id,
        "FACEBOOK_APP_SECRET": data.facebook_app_secret,
        "TELEGRAM_BOT_TOKEN": data.telegram_bot_token,
        "TELEGRAM_CHAT_ID": data.telegram_chat_id,
    }
    for env_key, value in oauth_fields.items():
        if value:
            os.environ[env_key] = value
            updated.append(env_key.lower())

    return {"updated": updated, "message": f"Updated {len(updated)} keys"}


@router.post("/keys/validate", summary="Validate an API key")
def validate_key(data: ValidateRequest):
    """Test if an API key works"""
    if data.service == "openaiKey":
        try:
            import openai
            client = openai.OpenAI(api_key=data.key)
            client.models.list()
            return {"valid": True, "message": "OpenAI key works!"}
        except Exception as e:
            raise HTTPException(400, f"Invalid key: {e}")

    elif data.service == "anthropicKey":
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=data.key)
            # Simple ping — count tokens to verify key
            client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}],
            )
            return {"valid": True, "message": "Anthropic key works!"}
        except ImportError:
            raise HTTPException(400, "anthropic package not installed")
        except Exception as e:
            raise HTTPException(400, f"Invalid key: {e}")

    elif data.service == "geminiKey":
        try:
            from google import genai
            client = genai.Client(api_key=data.key)
            # List models to verify key
            client.models.list()
            return {"valid": True, "message": "Google Gemini key works!"}
        except ImportError:
            raise HTTPException(400, "google-genai package not installed")
        except Exception as e:
            raise HTTPException(400, f"Invalid key: {e}")

    elif data.service == "pexelsKey":
        try:
            r = requests.get(
                "https://api.pexels.com/v1/search",
                headers={"Authorization": data.key},
                params={"query": "test", "per_page": 1},
                timeout=5,
            )
            if r.status_code == 200:
                return {"valid": True, "message": "Pexels key works!"}
            raise HTTPException(400, f"Pexels returned {r.status_code}")
        except requests.RequestException as e:
            raise HTTPException(400, f"Pexels validation failed: {e}")

    elif data.service == "elevenlabsKey":
        try:
            r = requests.get(
                "https://api.elevenlabs.io/v1/user",
                headers={"xi-api-key": data.key},
                timeout=5,
            )
            if r.status_code == 200:
                return {"valid": True, "message": "ElevenLabs key works!"}
            raise HTTPException(400, f"ElevenLabs returned {r.status_code}")
        except requests.RequestException as e:
            raise HTTPException(400, f"Validation failed: {e}")

    return {"valid": False, "message": "Unknown service"}


@router.post("/telegram/test", summary="Test Telegram bot connection")
def test_telegram(data: TelegramTestRequest):
    """Send a test message to verify bot + chat ID"""
    try:
        url = f"https://api.telegram.org/bot{data.token}/sendMessage"
        r = requests.post(url, json={
            "chat_id": data.chat_id,
            "text": "✅ Content Bot connected successfully!",
            "parse_mode": "HTML",
        }, timeout=10)

        if r.status_code == 200:
            # Save to env
            os.environ["TELEGRAM_BOT_TOKEN"] = data.token
            os.environ["TELEGRAM_CHAT_ID"] = data.chat_id
            return {"success": True, "message": "Bot connected!"}

        raise HTTPException(400, f"Telegram error: {r.text}")
    except requests.RequestException as e:
        raise HTTPException(400, f"Connection failed: {e}")


class TelegramDetectRequest(BaseModel):
    token: str


@router.post("/telegram/detect-chat", summary="Auto-detect Chat ID from /start message")
def detect_telegram_chat(data: TelegramDetectRequest):
    """
    Poll Telegram getUpdates to find a recent /start message.
    User should send /start to the bot, then call this endpoint.
    Returns the chat_id of the user who sent /start.
    """
    try:
        url = f"https://api.telegram.org/bot{data.token}/getUpdates"
        r = requests.get(url, params={"limit": 20, "timeout": 5}, timeout=15)

        if r.status_code != 200:
            raise HTTPException(400, f"Invalid bot token or Telegram error: {r.text}")

        updates = r.json().get("result", [])

        # Find the most recent /start message
        for update in reversed(updates):
            msg = update.get("message", {})
            text = msg.get("text", "")
            if text.strip() == "/start":
                chat = msg.get("chat", {})
                chat_id = str(chat.get("id", ""))
                first_name = chat.get("first_name", "")
                username = chat.get("username", "")

                if chat_id:
                    # Save immediately
                    os.environ["TELEGRAM_BOT_TOKEN"] = data.token
                    os.environ["TELEGRAM_CHAT_ID"] = chat_id

                    # Send confirmation
                    requests.post(
                        f"https://api.telegram.org/bot{data.token}/sendMessage",
                        json={
                            "chat_id": chat_id,
                            "text": "✅ Connected! I'll notify you when videos are ready.",
                            "parse_mode": "HTML",
                        },
                        timeout=5,
                    )

                    return {
                        "found": True,
                        "chat_id": chat_id,
                        "name": first_name or username or "User",
                    }

        return {"found": False, "message": "No /start message found. Please send /start to your bot first."}

    except requests.RequestException as e:
        raise HTTPException(400, f"Connection failed: {e}")

