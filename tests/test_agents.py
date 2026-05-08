"""
Tests for Agent classes — Pipeline, BaseAgent, and individual agents.
"""

import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from backend.agents.base import BaseAgent
from backend.agents.schemas import AgentStatus
from backend.agents.pipeline import Pipeline


class TestBaseAgent:
    """Test BaseAgent behavior"""

    def test_default_values(self):
        agent = BaseAgent()
        assert agent.name == "BaseAgent"
        assert agent.max_retries == 3
        assert agent.is_critical is True
        assert agent.status == AgentStatus.IDLE

    def test_execute_not_implemented(self):
        agent = BaseAgent()
        with pytest.raises(NotImplementedError):
            agent.execute({})

    def test_skip_sets_status(self):
        agent = BaseAgent()
        agent.skip("test reason")
        assert agent.status == AgentStatus.SKIPPED

    def test_get_status_dict(self):
        agent = BaseAgent()
        status = agent.get_status_dict()
        assert status["agent"] == "BaseAgent"
        assert status["status"] == "idle"
        assert status["error"] is None

    def test_run_with_success(self):
        class SuccessAgent(BaseAgent):
            name = "SuccessAgent"
            def execute(self, context):
                return {"result_key": "value"}

        agent = SuccessAgent()
        ctx = {}
        result = agent.run(ctx)
        assert agent.status == AgentStatus.SUCCESS
        assert result["result_key"] == "value"

    def test_run_with_failure(self):
        class FailAgent(BaseAgent):
            name = "FailAgent"
            max_retries = 1
            def execute(self, context):
                raise RuntimeError("Test error")

        agent = FailAgent()
        with pytest.raises(RuntimeError, match="Test error"):
            agent.run({})
        assert agent.status == AgentStatus.FAILED


class TestPipeline:
    """Test Pipeline orchestration"""

    def test_init_context(self):
        pipeline = Pipeline()
        ctx = pipeline._init_context({
            "source_url": "https://example.com",
            "platforms": ["tiktok", "youtube"],
            "language": "vi",
            "video_count": 2,
        })
        assert ctx["source_url"] == "https://example.com"
        assert ctx["platforms"] == ["tiktok", "youtube"]
        assert ctx["language"] == "vi"
        assert ctx["video_count"] == 2
        assert ctx["agent_results"] == []

    def test_save_and_load_checkpoint(self, tmp_job_dir):
        pipeline = Pipeline()
        ctx = {
            "job_id": "test-001",
            "job_dir": tmp_job_dir,
            "source_url": "https://example.com",
            "last_checkpoint": "TestAgent",
            "some_data": "hello",
        }
        pipeline._save_checkpoint(ctx)

        # Verify file exists
        checkpoint = Path(tmp_job_dir) / "checkpoint.json"
        assert checkpoint.exists()

        # Load and verify
        loaded = pipeline._load_checkpoint(
            {"job_dir": tmp_job_dir}, "TestAgent"
        )
        assert loaded["some_data"] == "hello"

    def test_run_empty_pipeline(self, sample_context):
        pipeline = Pipeline(agents=[])
        result = pipeline.run({"source_url": "https://example.com"})
        assert result["pipeline_status"] == "completed"

    def test_pipeline_skip_non_critical(self, sample_context):
        class NonCriticalFail(BaseAgent):
            name = "NonCriticalFail"
            is_critical = False
            max_retries = 1
            def execute(self, context):
                raise RuntimeError("Non-critical failure")

        class SuccessAfter(BaseAgent):
            name = "SuccessAfter"
            def execute(self, context):
                return {"after": True}

        pipeline = Pipeline(agents=[NonCriticalFail(), SuccessAfter()])
        result = pipeline.run({"source_url": "https://example.com"})
        assert result["pipeline_status"] == "completed"
        assert result["after"] is True

    def test_pipeline_stop_on_critical(self):
        class CriticalFail(BaseAgent):
            name = "CriticalFail"
            is_critical = True
            max_retries = 1
            def execute(self, context):
                raise RuntimeError("Critical failure")

        pipeline = Pipeline(agents=[CriticalFail()])
        result = pipeline.run({"source_url": "https://example.com"})
        assert result["pipeline_status"] == "failed"


class TestContentFetcherAgent:
    """Test content fetcher"""

    def test_fetch_document(self, tmp_job_dir, sample_txt):
        from backend.agents.fetcher import ContentFetcherAgent

        agent = ContentFetcherAgent()
        ctx = {
            "source_url": sample_txt,
            "source_type": "document",
            "source_document_path": sample_txt,
            "job_dir": tmp_job_dir,
        }
        result = agent.run(ctx)
        assert "content_data" in result
        assert result["content_data"]["source_type"] == "document"
        assert "Test Document" in result["content_data"]["title"]


class TestABTestAgent:
    """Test A/B testing agent"""

    @patch("backend.agents.ab_testing.get_llm_client")
    def test_ab_testing_generates_variants(self, mock_get_llm, tmp_job_dir, sample_scripts):
        mock_llm = MagicMock()
        mock_llm.generate_json.return_value = [
            {"variant": "A", "variant_label": "Original", "title": "Test", "hook": "Hook A"},
            {"variant": "B", "variant_label": "Question", "title": "Test", "hook": "Hook B?"},
        ]
        mock_get_llm.return_value = mock_llm

        from backend.agents.ab_testing import ABTestAgent

        agent = ABTestAgent()
        ctx = {
            "scripts": sample_scripts,
            "job_dir": tmp_job_dir,
            "ab_variant_count": 2,
        }
        result = agent.run(ctx)
        assert result["ab_testing_enabled"] is True
        assert result["ab_variant_count"] >= 2

    def test_ab_no_scripts(self, tmp_job_dir):
        from backend.agents.ab_testing import ABTestAgent

        agent = ABTestAgent()
        result = agent.execute({"scripts": [], "job_dir": tmp_job_dir})
        assert result["ab_testing_enabled"] is False


class TestPipelineAIImageIntegration:
    """Integration tests: AIImageAgent in the pipeline"""

    @patch.dict(os.environ, {
        "PIXELLE_ENABLED": "true",
        "PIXELLE_VIDEO_API_URL": "http://pixelle:8085",
        "OPENAI_API_KEY": "",
    }, clear=True)
    def test_default_pipeline_includes_ai_image_agent(self):
        """PIXELLE_ENABLED=true -> AIImageAgent is part of default pipeline"""
        with patch("backend.core.pixelle_client.PixelleClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.is_available.return_value = True
            mock_client_class.return_value = mock_client

            pipeline = Pipeline.default()
            agent_names = [a.name for a in pipeline.agents]

            assert "AIImageAgent" in agent_names, (
                f"AIImageAgent not found: {agent_names}"
            )
            # Must be before VoiceGenerator
            ai_idx = agent_names.index("AIImageAgent")
            voice_idx = agent_names.index("VoiceGeneratorAgent")
            assert ai_idx < voice_idx, "AIImageAgent must run before VoiceGeneratorAgent"

    @patch.dict(os.environ, {
        "PIXELLE_ENABLED": "false",
        "PIXELLE_VIDEO_API_URL": "http://localhost:8085",
        "OPENAI_API_KEY": "",
    }, clear=True)
    def test_default_pipeline_excludes_ai_image_when_disabled(self):
        """Without Pixelle or DALL-E -> AIImageAgent not in pipeline"""
        pipeline = Pipeline.default()
        agent_names = [a.name for a in pipeline.agents]
        assert "AIImageAgent" not in agent_names, (
            f"AIImageAgent should not be in pipeline when disabled: {agent_names}"
        )

    def test_ai_image_agent_is_non_critical(self):
        """AIImageAgent failure should not stop the pipeline"""
        from backend.agents.ai_image import AIImageAgent

        ai_agent = AIImageAgent()
        assert ai_agent.is_critical is False, (
            "AIImageAgent must be non-critical for Pexels fallback"
        )

        class SuccessAfter(BaseAgent):
            name = "SuccessAfter"
            def execute(self, context):
                return {"pipeline_continued": True}

        class FailingAIImage(BaseAgent):
            name = "AIImageAgent"
            is_critical = False
            max_retries = 1
            def execute(self, context):
                raise RuntimeError("AI image service unavailable")

        pipeline = Pipeline(agents=[FailingAIImage(), SuccessAfter()])
        result = pipeline.run({"source_url": "https://example.com"})
        assert result["pipeline_status"] == "completed"
        assert result["pipeline_continued"] is True

    def test_ai_image_context_keys_match_composer_expectation(self, tmp_path):
        """Verify AIImageAgent output keys match what Composer expects"""
        expected_keys = {
            "ai_images", "ai_images_available", "ai_images_count",
            "ai_images_dir", "ai_images_provider",
        }

        # Simulate the context after AIImageAgent runs
        context = {
            "scripts": [{
                "script_id": 1,
                "title": "Test",
                "hook": "Amazing!",
                "cta": "Subscribe!",
                "scenes": [{"scene_id": 1, "text": "Hello", "duration": 5}],
            }],
            "job_dir": str(tmp_path),
            "language": "vi",
            "ai_images": {"1": [{"type": "scene", "scene_id": 1, "path": "/tmp/img.png"}]},
            "ai_images_available": True,
            "ai_images_count": 1,
            "ai_images_dir": str(tmp_path / "ai_images"),
            "ai_images_provider": "pixelle",
        }

        # Verify all expected keys are present
        for key in expected_keys:
            assert key in context, f"Composer expects '{key}' in context"
        assert isinstance(context["ai_images"], dict)
        assert context["ai_images_available"] is True