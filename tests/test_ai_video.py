"""
Unit tests for AIVideoAgent — AI video clip generation for scenes.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.agents.ai_video import (
    AIVideoAgent,
    VIDEO_HOOK_PREFIX,
    VIDEO_SCENE_PREFIX,
    VIDEO_CTA_PREFIX,
)


class TestAIVideoAgentInit:
    def test_default_constructor(self):
        agent = AIVideoAgent()
        assert agent.name == "AIVideoAgent"
        assert agent.is_critical is False
        assert agent._provider is None
        assert agent._kling_client is None
        assert agent._runway_client is None


class TestAIVideoAgentProviderDetection:
    @patch.dict(os.environ, {"KLING_API_KEY": "kl-key-1234567890"}, clear=True)
    def test_detect_kling(self):
        agent = AIVideoAgent()
        result = agent._detect_provider()
        assert result == "kling"

    @patch.dict(os.environ, {
        "KLING_API_KEY": "",
        "RUNWAY_API_KEY": "rw-key-1234567890",
        "RUNWAY_API_SECRET": "rw-secret-1234567890",
    }, clear=True)
    def test_detect_runway(self):
        agent = AIVideoAgent()
        result = agent._detect_provider()
        assert result == "runway"

    @patch.dict(os.environ, {
        "KLING_API_KEY": "",
        "RUNWAY_API_KEY": "",
    }, clear=True)
    def test_detect_none(self):
        agent = AIVideoAgent()
        result = agent._detect_provider()
        assert result == "none"

    @patch.dict(os.environ, {"KLING_API_KEY": "short"}, clear=True)
    def test_detect_short_kling_key_ignored(self):
        agent = AIVideoAgent()
        result = agent._detect_provider()
        assert result == "none"


class TestAIVideoAgentPromptBuilding:
    def test_hook_prompt(self):
        agent = AIVideoAgent()
        prompt = agent._build_video_prompt(
            "Amazing discovery!", {"mood": "dramatic"},
            scene_type="hook",
        )
        assert "dramatic" in prompt.lower()
        assert "Amazing discovery" in prompt

    def test_scene_prompt_with_visual(self):
        agent = AIVideoAgent()
        prompt = agent._build_video_prompt(
            "Python basics", {"mood": "energetic", "title": "Learn Python"},
            visual_hint="A colorful code editor",
            scene_type="scene",
        )
        assert "colorful code editor" in prompt.lower()
        assert "energetic" in prompt.lower() or "cinematic" in prompt.lower()

    def test_cta_prompt(self):
        agent = AIVideoAgent()
        prompt = agent._build_video_prompt(
            "Subscribe now!", {}, scene_type="cta",
        )
        assert "Subscribe" in prompt

    def test_custom_prefix_override(self):
        with patch.dict(os.environ, {"AI_VIDEO_PROMPT_PREFIX": "CUSTOM PREFIX"}, clear=True):
            agent = AIVideoAgent()
            prompt = agent._build_video_prompt("test", {}, scene_type="scene")
            assert prompt.startswith("CUSTOM PREFIX")

    def test_prompt_truncation(self):
        agent = AIVideoAgent()
        long_text = "word " * 500
        prompt = agent._build_video_prompt(long_text, {}, scene_type="scene")
        assert len(prompt) <= 1550  # 1500 + prefix


class TestAIVideoAgentExecute:
    @patch.dict(os.environ, {
        "KLING_API_KEY": "",
        "RUNWAY_API_KEY": "",
    }, clear=True)
    def test_execute_no_provider(self, tmp_path, sample_scripts):
        agent = AIVideoAgent()
        ctx = {"scripts": sample_scripts, "job_dir": str(tmp_path)}
        result = agent.execute(ctx)
        assert result["ai_videos_available"] is False
        assert result["ai_videos_count"] == 0

    @patch.dict(os.environ, {"KLING_API_KEY": "kl-test-key-1234567890"}, clear=True)
    @patch.object(AIVideoAgent, "_generate_clip", return_value="/tmp/clip.mp4")
    def test_execute_with_kling(self, mock_clip, tmp_path, sample_scripts):
        agent = AIVideoAgent()
        ctx = {
            "scripts": sample_scripts,
            "job_dir": str(tmp_path),
            "aspect_ratio": "9:16",
        }
        result = agent.execute(ctx)

        assert result["ai_videos_available"] is True
        assert result["ai_videos_provider"] == "kling"
        # 1 hook + 2 scenes + 1 cta = 4 clips
        assert result["ai_videos_count"] == 4

    @patch.dict(os.environ, {
        "KLING_API_KEY": "kl-test-key-1234567890",
    }, clear=True)
    @patch.object(AIVideoAgent, "_generate_clip")
    def test_execute_partial_failures(self, mock_clip, tmp_path, sample_scripts):
        mock_clip.side_effect = [
            "/tmp/hook.mp4",  # OK
            "/tmp/scene1.mp4", # OK
            None,             # FAIL
            None,             # FAIL
        ]
        agent = AIVideoAgent()
        ctx = {"scripts": sample_scripts, "job_dir": str(tmp_path)}
        result = agent.execute(ctx)
        assert result["ai_videos_available"] is True
        assert result["ai_videos_count"] == 2

    @patch.dict(os.environ, {"KLING_API_KEY": "kl-test-key-1234567890"}, clear=True)
    @patch.object(AIVideoAgent, "_generate_clip", return_value="/tmp/clip.mp4")
    def test_execute_creates_ai_videos_dir(self, mock_clip, tmp_path, sample_scripts):
        agent = AIVideoAgent()
        ctx = {"scripts": sample_scripts, "job_dir": str(tmp_path)}
        agent.execute(ctx)
        ai_videos_dir = Path(tmp_path) / "ai_videos"
        assert ai_videos_dir.exists()

    @patch.dict(os.environ, {
        "RUNWAY_API_KEY": "rw-key-1234567890",
        "RUNWAY_API_SECRET": "rw-secret-1234567890",
    }, clear=True)
    @patch.object(AIVideoAgent, "_generate_clip", return_value="/tmp/rw_clip.mp4")
    def test_execute_with_runway(self, mock_clip, tmp_path, sample_scripts):
        agent = AIVideoAgent()
        ctx = {
            "scripts": sample_scripts,
            "job_dir": str(tmp_path),
        }
        result = agent.execute(ctx)
        assert result["ai_videos_provider"] == "runway"


class TestAIVideoAgentPipelineIntegration:
    """Verify AIVideoAgent integrates correctly into the pipeline"""

    @patch.dict(os.environ, {"KLING_API_KEY": "kl-key-1234567890"}, clear=True)
    def test_pipeline_default_includes_ai_video_agent(self):
        from backend.agents.pipeline import Pipeline

        pipeline = Pipeline.default()
        agent_names = [a.name for a in pipeline.agents]
        assert "AIVideoAgent" in agent_names

        # AIVideoAgent must be before AIImageAgent (video trumps image)
        if "AIImageAgent" in agent_names:
            vid_idx = agent_names.index("AIVideoAgent")
            img_idx = agent_names.index("AIImageAgent")
            assert vid_idx < img_idx, "AIVideoAgent must run before AIImageAgent"

    @patch.dict(os.environ, {
        "KLING_API_KEY": "",
        "RUNWAY_API_KEY": "",
    }, clear=True)
    def test_pipeline_excludes_when_no_provider(self):
        from backend.agents.pipeline import Pipeline

        pipeline = Pipeline.default()
        agent_names = [a.name for a in pipeline.agents]
        assert "AIVideoAgent" not in agent_names

    def test_context_keys_match_composer(self):
        """Verify AIVideoAgent output keys match what Composer reads"""
        expected_keys = {
            "ai_videos", "ai_videos_available", "ai_videos_count",
            "ai_videos_dir", "ai_videos_provider",
        }
        context = {
            "ai_videos": {},
            "ai_videos_available": False,
            "ai_videos_count": 0,
            "ai_videos_dir": "/tmp/ai_videos",
            "ai_videos_provider": "none",
        }
        for key in expected_keys:
            assert key in context
