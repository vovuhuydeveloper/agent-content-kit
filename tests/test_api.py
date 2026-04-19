"""
Tests for API endpoints.
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client"""
    from fastapi import FastAPI
    from backend.api.v1.config_api import router as config_router
    from backend.api.v1.schedule_api import router as schedule_router

    app = FastAPI()
    app.include_router(config_router, prefix="/api/v1")
    app.include_router(schedule_router, prefix="/api/v1")

    return TestClient(app)


class TestConfigAPI:
    """Test config endpoints"""

    def test_get_keys_masked(self, client):
        resp = client.get("/api/v1/config/keys")
        assert resp.status_code == 200
        data = resp.json()
        assert "openai_api_key" in data
        assert "anthropic_api_key" in data
        assert "google_api_key" in data
        assert "llm_provider" in data

    @patch.dict("os.environ", {"OPENAI_API_KEY": ""})
    def test_save_keys(self, client):
        resp = client.post("/api/v1/config/keys", json={
            "openai_api_key": "sk-test-new-key",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "openai" in data["updated"]

    def test_save_llm_provider(self, client):
        with patch("backend.core.llm_manager.reset_llm_manager"):
            resp = client.post("/api/v1/config/keys", json={
                "llm_provider": "claude",
            })
            assert resp.status_code == 200
            assert "llm_provider" in resp.json()["updated"]


class TestAnalyticsAPI:
    """Test analytics API — integration test via full app"""

    def test_overview_via_main_app(self):
        """Test analytics endpoint via the main app (uses real DB)"""
        from backend.main import app
        from backend.core.database import create_tables
        create_tables()

        test_client = TestClient(app)
        resp = test_client.get("/api/v1/analytics/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_videos" in data
        assert "total_views" in data
        assert "period_days" in data
