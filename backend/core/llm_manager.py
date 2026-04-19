"""
LLM Manager — Multi-provider LLM support.
Supports OpenAI, Anthropic Claude, and Google Gemini.

Usage:
    manager = get_llm_manager()
    response = manager.call("Tell me about Python")
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger("core.llm_manager")


# ──────────────────────────────
# Abstract Base Provider
# ──────────────────────────────

class LLMProvider(ABC):
    """Base class for all LLM providers"""

    def __init__(self, api_key: str, model: str, temperature: float = 0.7,
                 max_tokens: int = 4096):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    @abstractmethod
    def call(self, prompt: str, system: Optional[str] = None) -> str:
        """Generate text from prompt. Returns raw text string."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...


# ──────────────────────────────
# OpenAI Provider
# ──────────────────────────────

class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider (GPT-4o-mini, GPT-4o, etc.)"""

    provider_name = "openai"

    def call(self, prompt: str, system: Optional[str] = None) -> str:
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("openai package not installed. Run: pip install openai")

        client = OpenAI(api_key=self.api_key)

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        return response.choices[0].message.content.strip()


# ──────────────────────────────
# Anthropic Claude Provider
# ──────────────────────────────

class ClaudeProvider(LLMProvider):
    """Anthropic Claude provider (Claude Sonnet, Opus, Haiku)"""

    provider_name = "claude"

    # Default model mapping
    MODEL_MAP = {
        "claude-sonnet": "claude-sonnet-4-20250514",
        "claude-opus": "claude-opus-4-20250514",
        "claude-haiku": "claude-haiku-4-20250514",
    }

    def call(self, prompt: str, system: Optional[str] = None) -> str:
        try:
            import anthropic
        except ImportError:
            raise RuntimeError("anthropic package not installed. Run: pip install anthropic")

        client = anthropic.Anthropic(api_key=self.api_key)

        # Resolve short name → full model ID
        model = self.MODEL_MAP.get(self.model, self.model)

        kwargs = {
            "model": model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        response = client.messages.create(**kwargs)

        # Extract text from content blocks
        return "".join(
            block.text for block in response.content if hasattr(block, "text")
        ).strip()


# ──────────────────────────────
# Google Gemini Provider
# ──────────────────────────────

class GeminiProvider(LLMProvider):
    """Google Gemini provider (Gemini 2.5 Pro, Flash, etc.)"""

    provider_name = "gemini"

    # Default model mapping
    MODEL_MAP = {
        "gemini-pro": "gemini-2.5-pro-preview-05-06",
        "gemini-flash": "gemini-2.5-flash-preview-05-20",
    }

    def call(self, prompt: str, system: Optional[str] = None) -> str:
        try:
            from google import genai
        except ImportError:
            raise RuntimeError(
                "google-genai package not installed. Run: pip install google-genai"
            )

        client = genai.Client(api_key=self.api_key)

        # Resolve short name → full model ID
        model = self.MODEL_MAP.get(self.model, self.model)

        # Build config
        config = {
            "temperature": self.temperature,
            "max_output_tokens": self.max_tokens,
        }
        if system:
            config["system_instruction"] = system

        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=config,
        )

        return response.text.strip()


# ──────────────────────────────
# Manager (Factory)
# ──────────────────────────────

PROVIDERS = {
    "openai": OpenAIProvider,
    "claude": ClaudeProvider,
    "anthropic": ClaudeProvider,  # alias
    "gemini": GeminiProvider,
    "google": GeminiProvider,  # alias
}

# Default models per provider
DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "claude": "claude-sonnet-4-20250514",
    "anthropic": "claude-sonnet-4-20250514",
    "gemini": "gemini-2.5-flash-preview-05-20",
    "google": "gemini-2.5-flash-preview-05-20",
}


class LLMManager:
    """
    Unified LLM manager — wraps a single provider.

    Resolution order for API key:
    1. Explicit api_key parameter
    2. Environment variable (OPENAI_API_KEY / ANTHROPIC_API_KEY / GOOGLE_API_KEY)
    3. Config settings
    """

    def __init__(
        self,
        provider: str = "openai",
        api_key: str = "",
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        provider = provider.lower()
        if provider not in PROVIDERS:
            raise ValueError(
                f"Unknown LLM provider: {provider}. "
                f"Supported: {list(PROVIDERS.keys())}"
            )

        # Resolve API key from env if not provided
        if not api_key:
            env_keys = {
                "openai": "OPENAI_API_KEY",
                "claude": "ANTHROPIC_API_KEY",
                "anthropic": "ANTHROPIC_API_KEY",
                "gemini": "GOOGLE_API_KEY",
                "google": "GOOGLE_API_KEY",
            }
            api_key = os.environ.get(env_keys.get(provider, ""), "")

        if not api_key:
            raise ValueError(
                f"No API key found for provider '{provider}'. "
                f"Set it via environment variable or config."
            )

        # Default model if not specified
        if not model:
            model = DEFAULT_MODELS.get(provider, "")

        self._provider: LLMProvider = PROVIDERS[provider](
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        logger.info(
            f"LLM Manager initialized: provider={provider}, model={model}"
        )

    def call(self, prompt: str, system: Optional[str] = None) -> str:
        """Generate text from LLM"""
        logger.debug(f"LLM call: provider={self._provider.provider_name}, "
                     f"prompt_len={len(prompt)}")
        return self._provider.call(prompt, system)

    @property
    def provider_name(self) -> str:
        return self._provider.provider_name

    @property
    def model(self) -> str:
        return self._provider.model


# ──────────────────────────────
# Singleton
# ──────────────────────────────

_manager: Optional[LLMManager] = None


def get_llm_manager() -> LLMManager:
    """
    Get or create the global LLM manager singleton.
    Uses settings from config.py to determine provider.
    """
    global _manager
    if _manager is None:
        try:
            from backend.core.config import settings
            provider = getattr(settings, "llm_provider", "openai")
            model = getattr(settings, "llm_model", "")
            temperature = getattr(settings, "llm_temperature", 0.7)

            # Try to get API key from config
            key_map = {
                "openai": "openai_api_key",
                "claude": "anthropic_api_key",
                "anthropic": "anthropic_api_key",
                "gemini": "google_api_key",
                "google": "google_api_key",
            }
            api_key = getattr(settings, key_map.get(provider, ""), "")

            _manager = LLMManager(
                provider=provider,
                api_key=api_key,
                model=model,
                temperature=temperature,
            )
        except Exception as e:
            logger.warning(f"Config-based init failed ({e}), trying env-based...")
            # Fallback: detect from environment
            provider = os.environ.get("LLM_PROVIDER", "openai")
            _manager = LLMManager(provider=provider)

    return _manager


def reset_llm_manager():
    """Reset the singleton (useful for testing or switching providers)"""
    global _manager
    _manager = None
