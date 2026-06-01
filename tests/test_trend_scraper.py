"""
Tests for TrendScraperAgent.
"""

from unittest.mock import patch, MagicMock

import pytest

from backend.agents.trend_scraper import TrendScraperAgent


class TestTrendScraper:
    """Test TrendScraperAgent"""

    @patch("backend.agents.trend_scraper.requests.get")
    def test_fallback_hashtags_when_api_fails(self, mock_get, tmp_job_dir):
        mock_get.side_effect = Exception("Connection refused")

        agent = TrendScraperAgent()
        result = agent.execute({
            "niche": "education",
            "language": "vi",
            "job_dir": tmp_job_dir,
        })

        hashtags = result["trends"]["hashtags"]
        assert len(hashtags) >= 3
        assert hashtags[0]["name"] == "education"

    @patch("backend.agents.trend_scraper.requests.get")
    def test_fetches_real_hashtags(self, mock_get, tmp_job_dir):
        mock_hashtag_response = MagicMock()
        mock_hashtag_response.status_code = 200
        mock_hashtag_response.json.return_value = {
            "data": {
                "list": [
                    {"hashtag_name": "fyp", "video_views": 1000000, "publish_cnt": 5000, "trend": 1},
                    {"hashtag_name": "viral", "video_views": 800000, "publish_cnt": 3000, "trend": 1},
                    {"hashtag_name": "learnontiktok", "video_views": 500000, "publish_cnt": 2000, "trend": 1},
                ]
            }
        }

        mock_sound_response = MagicMock()
        mock_sound_response.status_code = 200
        mock_sound_response.json.return_value = {
            "data": {
                "list": [
                    {"title": "Popular Sound", "author": "Artist1", "video_cnt": 10000},
                ]
            }
        }

        mock_get.side_effect = [mock_hashtag_response, mock_sound_response]

        agent = TrendScraperAgent()
        result = agent.execute({
            "niche": "entertainment",
            "language": "vi",
            "job_dir": tmp_job_dir,
        })

        hashtags = result["trends"]["hashtags"]
        assert len(hashtags) == 3
        assert hashtags[0]["name"] == "fyp"
        assert hashtags[0]["views"] == 1000000

        sounds = result["trends"]["sounds"]
        assert len(sounds) == 1
        assert sounds[0]["title"] == "Popular Sound"

    @patch("backend.agents.trend_scraper.requests.get")
    def test_fallback_includes_niche(self, mock_get, tmp_job_dir):
        mock_get.side_effect = Exception("API down")

        agent = TrendScraperAgent()
        result = agent.execute({
            "niche": "cooking recipes",
            "language": "en",
            "job_dir": tmp_job_dir,
        })

        hashtags = result["trends"]["hashtags"]
        # Niche should appear first in fallback
        assert hashtags[0]["name"] == "cookingrecipes"
        assert "fyp" in [h["name"] for h in hashtags]
        assert "viral" in [h["name"] for h in hashtags]

    @patch("backend.agents.trend_scraper.requests.get")
    def test_no_niche_fallback(self, mock_get, tmp_job_dir):
        mock_get.side_effect = Exception("API down")

        agent = TrendScraperAgent()
        result = agent.execute({
            "niche": "",
            "language": "vi",
            "job_dir": tmp_job_dir,
        })

        hashtags = result["trends"]["hashtags"]
        assert len(hashtags) == 3
        assert hashtags[0]["name"] == "fyp"

    @patch("backend.agents.trend_scraper.requests.get")
    def test_handles_api_http_error(self, mock_get, tmp_job_dir):
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_get.return_value = mock_response

        agent = TrendScraperAgent()
        result = agent.execute({
            "niche": "tech",
            "language": "en",
            "job_dir": tmp_job_dir,
        })

        # Should fallback gracefully
        hashtags = result["trends"]["hashtags"]
        assert len(hashtags) >= 3
