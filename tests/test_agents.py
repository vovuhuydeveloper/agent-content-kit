"""
Tests for Agent classes — Pipeline, BaseAgent, and individual agents.
"""

import json
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
