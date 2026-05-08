"""
Unit tests for AIImageAgent — AI image generation for video scenes.

Covers: provider detection, prompt building, execute flow with mocked providers.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from backend.agents.ai_image import (
    AIImageAgent,
    HOOK_PROMPT_PREFIX,
    SCENE_PROMPT_PREFIX,
    CTA_PROMPT_PREFIX,
    VIRAL_STYLE_PRESETS,
)


class TestAIImageAgentInit:
    """Test agent initialization and basic properties"""

    def test_default_constructor(self):
        agent = AIImageAgent()
        assert agent.name == "AIImageAgent"
        assert agent.is_critical is False
        assert agent._provider is None
        assert agent._pixelle_client is None

    def test_constructor_with_config(self):
        config = {"some_setting": "value"}
        agent = AIImageAgent(config=config)
        assert agent.config == config


class TestAIImageAgentProviderDetection:
    """Test _detect_provider logic"""

    @patch.dict(os.environ, {
        "PIXELLE_ENABLED": "true",
        "PIXELLE_VIDEO_API_URL": "http://pixelle:8085",
        "OPENAI_API_KEY": "",
    }, clear=True)
    def test_detect_pixelle_enabled_flag(self):
        """PIXELLE_ENABLED=true should trigger Pixelle detection"""
        with patch("backend.core.pixelle_client.PixelleClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.is_available.return_value = True
            mock_client_class.return_value = mock_client

            agent = AIImageAgent()
            result = agent._detect_provider()
            assert result == "pixelle"

    @patch.dict(os.environ, {
        "PIXELLE_ENABLED": "false",
        "PIXELLE_VIDEO_API_URL": "http://real-pixelle-server:8085",
        "OPENAI_API_KEY": "",
    }, clear=True)
    def test_detect_pixelle_by_url(self):
        """Non-default URL should auto-detect Pixelle"""
        with patch("backend.core.pixelle_client.PixelleClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.is_available.return_value = True
            mock_client_class.return_value = mock_client

            agent = AIImageAgent()
            result = agent._detect_provider()
            assert result == "pixelle"

    @patch.dict(os.environ, {
        "PIXELLE_ENABLED": "false",
        "PIXELLE_VIDEO_API_URL": "http://localhost:8085",
        "OPENAI_API_KEY": "",
    }, clear=True)
    def test_detect_skip_default_pixelle_url(self):
        """Default localhost:8085 with PIXELLE_ENABLED=false should skip Pixelle"""
        agent = AIImageAgent()
        result = agent._detect_provider()
        assert result == "none"

    @patch.dict(os.environ, {
        "PIXELLE_ENABLED": "true",
        "OPENAI_API_KEY": "",
    }, clear=True)
    def test_detect_pixelle_unavailable(self):
        """Pixelle enabled but not reachable — should fall through"""
        with patch("backend.core.pixelle_client.PixelleClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.is_available.return_value = False
            mock_client_class.return_value = mock_client

            agent = AIImageAgent()
            result = agent._detect_provider()
            assert result == "none"

    @patch.dict(os.environ, {
        "OPENAI_API_KEY": "sk-test1234567890abcdef",
        "PIXELLE_ENABLED": "false",
    }, clear=True)
    def test_detect_dalle(self):
        """With OPENAI_API_KEY set, should fall back to DALL-E"""
        agent = AIImageAgent()
        result = agent._detect_provider()
        assert result == "dalle"

    @patch.dict(os.environ, {
        "OPENAI_API_KEY": "",
        "PIXELLE_ENABLED": "false",
    }, clear=True)
    def test_detect_none(self):
        """No provider configured"""
        agent = AIImageAgent()
        result = agent._detect_provider()
        assert result == "none"

    @patch.dict(os.environ, {
        "OPENAI_API_KEY": "short",
        "PIXELLE_ENABLED": "false",
    }, clear=True)
    def test_detect_short_api_key_ignored(self):
        """Very short API keys (invalid) should be ignored"""
        agent = AIImageAgent()
        result = agent._detect_provider()
        assert result == "none"


class TestAIImageAgentPromptPrefix:
    """Test prompt prefix selection"""

    def test_hook_prompt_prefix(self):
        agent = AIImageAgent()
        prefix = agent._get_prompt_prefix("hook")
        assert "hook" in prefix.lower()

    def test_scene_prompt_prefix(self):
        agent = AIImageAgent()
        prefix = agent._get_prompt_prefix("scene")
        assert "TikTok" in prefix

    def test_cta_prompt_prefix(self):
        agent = AIImageAgent()
        prefix = agent._get_prompt_prefix("cta")
        assert "call to action" in prefix.lower()

    def test_unknown_type_falls_back_to_scene(self):
        agent = AIImageAgent()
        prefix = agent._get_prompt_prefix("unknown_type")
        assert prefix == SCENE_PROMPT_PREFIX

    @patch.dict(os.environ, {
        "PIXELLE_IMAGE_PROMPT_PREFIX": "Custom prefix override",
    }, clear=True)
    def test_custom_prompt_prefix_env(self):
        agent = AIImageAgent()
        prefix = agent._get_prompt_prefix("hook")
        assert prefix == "Custom prefix override"

    @patch.dict(os.environ, {
        "VIRAL_STYLE": "neon",
    }, clear=True)
    def test_viral_style_neon_hook(self):
        agent = AIImageAgent()
        prefix = agent._get_prompt_prefix("hook")
        assert "maximum visual impact" in prefix
        assert "Neon" in prefix

    @patch.dict(os.environ, {
        "VIRAL_STYLE": "cinematic",
    }, clear=True)
    def test_viral_style_cinematic_scene(self):
        agent = AIImageAgent()
        prefix = agent._get_prompt_prefix("scene")
        assert "cinematic" in prefix.lower()

    @patch.dict(os.environ, {
        "VIRAL_STYLE": "minimal",
    }, clear=True)
    def test_viral_style_minimal_cta(self):
        agent = AIImageAgent()
        prefix = agent._get_prompt_prefix("cta")
        assert "call to action" in prefix.lower()
        assert "minimalist" in prefix.lower()

    @patch.dict(os.environ, {
        "VIRAL_STYLE": "nonexistent_style",
    }, clear=True)
    def test_viral_style_unknown_falls_back(self):
        """Unknown viral style should fall back to default prefixes"""
        agent = AIImageAgent()
        prefix = agent._get_prompt_prefix("hook")
        assert "hook" in prefix.lower()  # Default hook prefix


class TestAIImageAgentDimensions:
    """Test image dimension logic"""

    def test_9_16_portrait(self):
        agent = AIImageAgent()
        w, h = agent._get_image_dimensions("9:16")
        assert w == 1080
        assert h == 1920

    def test_16_9_landscape(self):
        agent = AIImageAgent()
        w, h = agent._get_image_dimensions("16:9")
        assert w == 1920
        assert h == 1080

    def test_1_1_square(self):
        agent = AIImageAgent()
        w, h = agent._get_image_dimensions("1:1")
        assert w == 1024
        assert h == 1024

    def test_default_unknown_ratio(self):
        agent = AIImageAgent()
        w, h = agent._get_image_dimensions("4:3")
        assert w == 1080  # Falls back to 9:16
        assert h == 1920

    def test_dalle_size_portrait(self):
        agent = AIImageAgent()
        size = agent._get_dalle_size(1080, 1920)
        assert size == "1024x1792"

    def test_dalle_size_landscape(self):
        agent = AIImageAgent()
        size = agent._get_dalle_size(1920, 1080)
        assert size == "1792x1024"

    def test_dalle_size_square(self):
        agent = AIImageAgent()
        size = agent._get_dalle_size(1024, 1024)
        assert size == "1024x1024"


class TestAIImageAgentVisualExtraction:
    """Test _extract_visual prompt building"""

    def test_extract_from_explicit_visual(self):
        agent = AIImageAgent()
        scene = {"visual": "A futuristic cityscape at sunset", "text": "Welcome"}
        script = {"title": "Futuristic Tech", "mood": "cinematic"}
        result = agent._extract_visual(scene, script, "en", "scene")
        assert "futuristic cityscape" in result.lower()

    def test_extract_from_text_fallback(self):
        agent = AIImageAgent()
        scene = {"text": "Learning Python is fun", "visual": ""}
        script = {"title": "Python Guide", "mood": "energetic"}
        result = agent._extract_visual(scene, script, "vi", "scene")
        assert "Python" in result
        assert "energetic" in result.lower()

    def test_extract_hook_enhances_prompt(self):
        agent = AIImageAgent()
        scene = {"visual": "Exciting explosion", "text": "Boom!"}
        script = {"title": "", "mood": ""}
        result = agent._extract_visual(scene, script, "en", "hook")
        assert "Viral hook visual" in result

    def test_extract_cta_enhances_prompt(self):
        agent = AIImageAgent()
        scene = {"visual": "Subscribe button", "text": "Follow us"}
        script = {"title": "", "mood": ""}
        result = agent._extract_visual(scene, script, "en", "cta")
        assert "Engagement prompt" in result

    def test_extract_includes_title(self):
        agent = AIImageAgent()
        scene = {"text": "Tutorial content", "visual": ""}
        script = {"title": "Mastering Python", "mood": "professional"}
        result = agent._extract_visual(scene, script, "en", "scene")
        assert "Mastering Python" in result


class TestAIImageAgentExecute:
    """Test the main execute() flow"""

    @patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key-1234567890"}, clear=True)
    def test_execute_no_scripts(self, tmp_path):
        agent = AIImageAgent()
        ctx = {
            "scripts": [],
            "job_dir": str(tmp_path),
            "language": "vi",
            "aspect_ratio": "9:16",
        }
        result = agent.execute(ctx)
        assert result["ai_images"] == {}
        assert result["ai_images_available"] is False
        assert result["ai_images_count"] == 0

    @patch.dict(os.environ, {
        "OPENAI_API_KEY": "",
        "PIXELLE_ENABLED": "false",
    }, clear=True)
    def test_execute_no_provider_available(self, tmp_path, sample_scripts):
        """No AI provider configured — should skip gracefully"""
        agent = AIImageAgent()
        ctx = {
            "scripts": sample_scripts,
            "job_dir": str(tmp_path),
            "language": "vi",
            "aspect_ratio": "9:16",
        }
        result = agent.execute(ctx)
        assert result["ai_images_available"] is False
        assert result["ai_images_count"] == 0

    @patch.object(AIImageAgent, "_detect_provider", return_value="dalle")
    @patch.object(AIImageAgent, "_generate_dalle")
    def test_execute_with_dalle_provider(
        self, mock_dalle, mock_detect, tmp_path, sample_scripts,
    ):
        """Mock DALL-E provider — verify images are generated for each segment"""
        mock_dalle.return_value = "/tmp/ai_img.png"

        agent = AIImageAgent()
        ctx = {
            "scripts": sample_scripts,
            "job_dir": str(tmp_path),
            "language": "vi",
            "aspect_ratio": "9:16",
        }
        result = agent.execute(ctx)

        assert result["ai_images_available"] is True
        # Each script: 1 hook + 2 scenes + 1 cta = 4 images
        assert result["ai_images_count"] == 4
        assert result["ai_images_provider"] == "dalle"
        assert "ai_images_dir" in result

        # Verify hook call was made with hook prefix
        hook_calls = [
            c for c in mock_dalle.call_args_list
            if c[0][5] == "hook"
        ]
        assert len(hook_calls) == 1

        # Verify scene calls
        scene_calls = [
            c for c in mock_dalle.call_args_list
            if c[0][5] == "scene"
        ]
        assert len(scene_calls) == 2

        # Verify CTA call
        cta_calls = [
            c for c in mock_dalle.call_args_list
            if c[0][5] == "cta"
        ]
        assert len(cta_calls) == 1

    @patch.object(AIImageAgent, "_detect_provider", return_value="dalle")
    @patch.object(AIImageAgent, "_generate_dalle")
    def test_execute_partial_failures(
        self, mock_dalle, mock_detect, tmp_path, sample_scripts,
    ):
        """Some images fail — should still report what succeeded"""
        # First 2 succeed, rest fail
        mock_dalle.side_effect = [
            "/tmp/hook.png",   # hook — OK
            "/tmp/scene1.png", # scene 1 — OK
            None,              # scene 2 — FAIL
            None,              # cta — FAIL
        ]

        agent = AIImageAgent()
        ctx = {
            "scripts": sample_scripts,
            "job_dir": str(tmp_path),
            "language": "vi",
            "aspect_ratio": "9:16",
        }
        result = agent.execute(ctx)

        assert result["ai_images_available"] is True
        assert result["ai_images_count"] == 2  # Only 2 succeeded

    @patch.object(AIImageAgent, "_detect_provider", return_value="pixelle")
    @patch.object(AIImageAgent, "_generate_pixelle")
    def test_execute_with_pixelle_provider(
        self, mock_pixelle, mock_detect, tmp_path, sample_scripts,
    ):
        """Mock Pixelle provider — verify pixelle is called, not dalle"""
        mock_pixelle.return_value = "/tmp/pixelle_img.png"

        agent = AIImageAgent()
        ctx = {
            "scripts": sample_scripts,
            "job_dir": str(tmp_path),
            "language": "vi",
            "aspect_ratio": "9:16",
        }
        result = agent.execute(ctx)

        assert result["ai_images_provider"] == "pixelle"
        assert result["ai_images_count"] == 4
        # All calls went to pixelle, not dalle
        assert mock_pixelle.call_count == 4

    @patch.object(AIImageAgent, "_detect_provider", return_value="dalle")
    @patch.object(AIImageAgent, "_generate_dalle", return_value="/tmp/img.png")
    def test_execute_creates_ai_images_dir(
        self, mock_dalle, mock_detect, tmp_path, sample_scripts,
    ):
        """Verify ai_images/ directory is created"""
        agent = AIImageAgent()
        ctx = {
            "scripts": sample_scripts,
            "job_dir": str(tmp_path),
            "language": "vi",
        }
        result = agent.execute(ctx)

        ai_images_dir = Path(tmp_path) / "ai_images"
        assert ai_images_dir.exists()
        assert ai_images_dir.is_dir()

    @patch.object(AIImageAgent, "_detect_provider", return_value="dalle")
    @patch.object(AIImageAgent, "_generate_dalle", return_value="/tmp/img.png")
    def test_execute_without_hook_and_cta(
        self, mock_dalle, mock_detect, tmp_path,
    ):
        """Script without hook and cta — should only generate scene images"""
        scripts = [{
            "script_id": 1,
            "title": "Test",
            "hook": "",
            "cta": "",
            "scenes": [
                {"scene_id": 1, "text": "Scene one", "visual": "Visual one"},
                {"scene_id": 2, "text": "Scene two", "visual": ""},
            ],
        }]

        agent = AIImageAgent()
        ctx = {
            "scripts": scripts,
            "job_dir": str(tmp_path),
            "language": "en",
        }
        result = agent.execute(ctx)

        # Only 2 scene images, no hook, no cta
        assert result["ai_images_count"] == 2
        scene_calls = [
            c for c in mock_dalle.call_args_list
            if c[0][5] == "scene"
        ]
        assert len(scene_calls) == 2

    def test_viral_style_presets_all_defined(self):
        """Sanity check: all viral style presets are non-empty"""
        assert len(VIRAL_STYLE_PRESETS) >= 5
        for name, prompt in VIRAL_STYLE_PRESETS.items():
            assert len(prompt) > 10, f"Style '{name}' prompt too short"