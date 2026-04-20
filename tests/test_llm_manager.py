"""
Tests for LLM Manager — Multi-provider LLM support.
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from backend.core.llm_manager import (
    LLMManager,
    OpenAIProvider,
    ClaudeProvider,
    GeminiProvider,
    get_llm_manager,
    reset_llm_manager,
    PROVIDERS,
    DEFAULT_MODELS,
)


class TestLLMProviderRegistry:
    """Test provider registration and defaults"""

    def test_all_providers_registered(self):
        assert "openai" in PROVIDERS
        assert "claude" in PROVIDERS
        assert "anthropic" in PROVIDERS  # alias
        assert "gemini" in PROVIDERS
        assert "google" in PROVIDERS  # alias

    def test_default_models_exist(self):
        assert "openai" in DEFAULT_MODELS
        assert "claude" in DEFAULT_MODELS
        assert "gemini" in DEFAULT_MODELS

    def test_provider_classes(self):
        assert PROVIDERS["openai"] is OpenAIProvider
        assert PROVIDERS["claude"] is ClaudeProvider
        assert PROVIDERS["anthropic"] is ClaudeProvider
        assert PROVIDERS["gemini"] is GeminiProvider
        assert PROVIDERS["google"] is GeminiProvider


class TestLLMManager:
    """Test LLM Manager initialization and routing"""

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            LLMManager(provider="nonexistent", api_key="test-key")

    def test_missing_key_raises(self):
        # Ensure no API keys leak from the real environment into this test
        with patch.dict(os.environ, {"OPENAI_API_KEY": "", "ANTHROPIC_API_KEY": "", "GOOGLE_API_KEY": ""}):
            with pytest.raises(ValueError, match="No API key found"):
                LLMManager(provider="openai", api_key="")

    def test_init_openai(self):
        manager = LLMManager(provider="openai", api_key="sk-test-key", model="gpt-4o-mini")
        assert manager.provider_name == "openai"
        assert manager.model == "gpt-4o-mini"

    def test_init_claude(self):
        manager = LLMManager(provider="claude", api_key="sk-ant-test", model="claude-sonnet-4-20250514")
        assert manager.provider_name == "claude"

    def test_init_gemini(self):
        manager = LLMManager(provider="gemini", api_key="google-test-key")
        assert manager.provider_name == "gemini"

    def test_alias_anthropic(self):
        manager = LLMManager(provider="anthropic", api_key="sk-ant-test")
        assert manager.provider_name == "claude"

    def test_alias_google(self):
        manager = LLMManager(provider="google", api_key="google-test-key")
        assert manager.provider_name == "gemini"

    def test_env_key_resolution(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-from-env"}):
            manager = LLMManager(provider="openai")
            assert manager.provider_name == "openai"

    def test_default_model_applied(self):
        manager = LLMManager(provider="openai", api_key="sk-test")
        assert manager.model == DEFAULT_MODELS["openai"]


class TestOpenAIProvider:
    """Test OpenAI provider"""

    @patch("openai.OpenAI")
    def test_call(self, mock_openai_class):
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Hello from GPT!"))]
        )

        provider = OpenAIProvider(api_key="sk-test", model="gpt-4o-mini")
        result = provider.call("Say hello")
        assert result == "Hello from GPT!"

    @patch("openai.OpenAI")
    def test_call_with_system(self, mock_openai_class):
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="System response"))]
        )

        provider = OpenAIProvider(api_key="sk-test", model="gpt-4o-mini")
        result = provider.call("Hello", system="You are helpful")
        
        # Verify system message was included
        call_kwargs = mock_client.chat.completions.create.call_args
        messages = call_kwargs.kwargs.get("messages", call_kwargs[1].get("messages", []))
        assert len(messages) == 2
        assert messages[0]["role"] == "system"


class TestSingleton:
    """Test get_llm_manager singleton"""

    def teardown_method(self):
        reset_llm_manager()

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-singleton", "LLM_PROVIDER": "openai"})
    def test_singleton_returns_same_instance(self):
        reset_llm_manager()
        m1 = get_llm_manager()
        m2 = get_llm_manager()
        assert m1 is m2

    def test_reset_clears_singleton(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test1", "LLM_PROVIDER": "openai"}):
            reset_llm_manager()
            m1 = get_llm_manager()
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test2", "LLM_PROVIDER": "openai"}):
            reset_llm_manager()
            m2 = get_llm_manager()
        assert m1 is not m2
