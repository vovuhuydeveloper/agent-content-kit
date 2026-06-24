"""
Tests for CompetitorAnalyzerAgent.
"""

import json
from unittest.mock import patch, MagicMock

import pytest

from backend.agents.analyzer import CompetitorAnalyzerAgent
from backend.agents.schemas import AgentStatus


class TestCompetitorAnalyzer:
    """Test CompetitorAnalyzerAgent"""

    def test_skip_when_no_urls(self):
        agent = CompetitorAnalyzerAgent()
        result = agent.execute({"competitor_urls": []})
        assert agent.status == AgentStatus.SKIPPED
        assert result == {}

    def test_is_non_critical(self):
        agent = CompetitorAnalyzerAgent()
        assert agent.is_critical is False

    @patch("subprocess.run")
    @patch("backend.agents.llm_client.get_llm_client")
    def test_execute_with_mock_ytdlp(self, mock_get_llm, mock_run):
        # Mock LLM response
        mock_llm = MagicMock()
        mock_llm.generate_json.return_value = {
            "common_hooks": ["Question hook", "Shock value"],
            "content_structures": ["Listicle", "Tutorial"],
            "trending_hashtags": ["#viral", "#trending"],
            "engagement_patterns": ["Short videos perform better"],
            "differentiation_opportunities": ["Unique niche angle"],
            "competitors_analyzed": 2,
        }
        mock_get_llm.return_value = mock_llm

        # Mock subprocess for metadata (first call)
        metadata_result = MagicMock()
        metadata_result.returncode = 0
        metadata_result.stdout = json.dumps({
            "title": "Competitor Video 1",
            "description": "A great video about testing",
            "duration": 120,
            "view_count": 50000,
            "like_count": 2000,
            "upload_date": "20250101",
            "tags": ["python", "testing", "tutorial"],
            "categories": ["Education"],
        })

        # Mock subprocess for transcript (second call) - produces no subs
        transcript_result = MagicMock()
        transcript_result.returncode = 0
        transcript_result.stdout = ""

        mock_run.side_effect = [metadata_result, transcript_result,
                                metadata_result, transcript_result]

        agent = CompetitorAnalyzerAgent()
        context = {
            "competitor_urls": [
                "https://youtube.com/watch?v=abc123",
                "https://youtube.com/watch?v=def456",
            ],
            "niche": "education",
            "language": "en",
            "job_dir": "/tmp/test",
        }
        result = agent.execute(context)

        assert "competitor_insights" in result
        insights = result["competitor_insights"]
        assert insights["competitors_analyzed"] == 2
        assert "common_hooks" in insights
        assert "content_structures" in insights
        assert "trending_hashtags" in insights
        assert "engagement_patterns" in insights
        assert "differentiation_opportunities" in insights

    @patch("subprocess.run")
    def test_graceful_failure_on_ytdlp_error(self, mock_run):
        """Non-critical: pipeline continues even if all fetches fail."""
        mock_run.side_effect = Exception("yt-dlp not found")

        agent = CompetitorAnalyzerAgent()
        context = {
            "competitor_urls": ["https://youtube.com/watch?v=badurl"],
            "niche": "education",
            "language": "en",
            "job_dir": "/tmp/test",
        }
        result = agent.run(context)

        assert "competitor_insights" in result
        assert result["competitor_insights"]["competitors_analyzed"] == 0
        assert agent.status == AgentStatus.SUCCESS

    @patch("subprocess.run")
    @patch("backend.agents.llm_client.get_llm_client")
    def test_fallback_analysis_when_llm_fails(self, mock_get_llm, mock_run):
        """Fallback heuristics should return structured insights when LLM fails."""
        mock_get_llm.side_effect = Exception("LLM unavailable")

        metadata_result = MagicMock()
        metadata_result.returncode = 0
        metadata_result.stdout = json.dumps({
            "title": "Test Video",
            "description": "Test",
            "duration": 60,
            "view_count": 1000,
            "like_count": 100,
            "upload_date": "20250101",
            "tags": ["python", "ai"],
            "categories": ["Science"],
        })

        transcript_result = MagicMock()
        transcript_result.returncode = 0
        transcript_result.stdout = ""

        mock_run.side_effect = [metadata_result, transcript_result]

        agent = CompetitorAnalyzerAgent()
        context = {
            "competitor_urls": ["https://youtube.com/watch?v=test123"],
            "niche": "tech",
            "language": "en",
            "job_dir": "/tmp/test",
        }
        result = agent.execute(context)

        insights = result["competitor_insights"]
        assert insights["competitors_analyzed"] == 1
        assert len(insights["common_hooks"]) > 0
        assert len(insights["trending_hashtags"]) > 0
        assert "python" in insights["trending_hashtags"]

    def test_extract_text_from_subtitles(self):
        agent = CompetitorAnalyzerAgent()
        raw_srt = (
            "1\n"
            "00:00:01,000 --> 00:00:04,000\n"
            "Welcome to this tutorial\n"
            "\n"
            "2\n"
            "00:00:05,000 --> 00:00:08,000\n"
            "Today we learn about Python testing\n"
        )
        text = agent._extract_text_from_subtitles(raw_srt)
        assert "Welcome to this tutorial" in text
        assert "Python testing" in text
        assert "00:00:01" not in text  # No timestamps
        assert "1" not in text.split()  # No index numbers

    def test_extract_text_from_vtt(self):
        agent = CompetitorAnalyzerAgent()
        raw_vtt = (
            "WEBVTT\n"
            "Kind: captions\n"
            "Language: en\n"
            "\n"
            "00:00:01.000 --> 00:00:04.000\n"
            "Hello world\n"
            "\n"
            "00:00:05.000 --> 00:00:08.000\n"
            "Testing is fun\n"
        )
        text = agent._extract_text_from_subtitles(raw_vtt)
        assert "Hello world" in text
        assert "Testing is fun" in text
        assert "WEBVTT" not in text
        assert "-->" not in text
