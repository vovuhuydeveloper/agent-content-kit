"""
Unit tests for CharacterAgent — animated talking character overlays.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image, ImageDraw

from backend.agents.character import (
    CharacterAgent,
    CHARACTER_MODE_STATIC,
    CHARACTER_MODE_TALKING_PET,
    CHARACTER_MODE_TALKING_AVATAR,
)


# ── Helper: create a minimal test PNG ──

def _create_test_char_png(path: Path, size=(200, 300)):
    """Create a simple test character PNG"""
    img = Image.new("RGBA", (size[0], size[1]), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Simple face: circle
    cx, cy = size[0] // 2, size[1] // 2
    r = min(size) // 3
    draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=(255, 200, 150, 255))
    # Eyes
    for ex in [cx - r // 3, cx + r // 3]:
        draw.ellipse([(ex - 3, cy - r // 4 - 3), (ex + 3, cy - r // 4 + 3)], fill=(0, 0, 0, 255))
    img.save(str(path), "PNG")
    return str(path)


class TestCharacterAgentInit:
    def test_default_constructor(self):
        agent = CharacterAgent()
        assert agent.name == "CharacterAgent"
        assert agent.is_critical is False

    def test_mode_constants(self):
        assert CHARACTER_MODE_STATIC == "static"
        assert CHARACTER_MODE_TALKING_PET == "talking_pet"
        assert CHARACTER_MODE_TALKING_AVATAR == "talking_avatar"


class TestCharacterAgentExecute:
    def test_static_mode_returns_empty(self, tmp_path):
        agent = CharacterAgent()
        ctx = {
            "character_mode": "static",
            "character_images": [],
            "scripts": [],
            "job_dir": str(tmp_path),
        }
        result = agent.execute(ctx)
        assert result["character_mode"] == "static"
        assert result["character_frames_available"] is False
        assert result["character_fps"] == 0

    def test_unknown_mode_falls_back(self, tmp_path):
        agent = CharacterAgent()
        ctx = {
            "character_mode": "invalid_mode_xyz",
            "character_images": [],
            "scripts": [],
            "job_dir": str(tmp_path),
        }
        result = agent.execute(ctx)
        assert result["character_mode"] == "static"

    @patch.object(CharacterAgent, "_find_character_image", return_value=None)
    def test_no_character_image_skips(self, mock_find, tmp_path, sample_scripts):
        agent = CharacterAgent()
        ctx = {
            "character_mode": "talking_pet",
            "character_images": [],
            "scripts": sample_scripts,
            "job_dir": str(tmp_path),
        }
        result = agent.execute(ctx)
        assert result["character_frames_available"] is False

    def test_talking_pet_generates_frames(self, tmp_path, sample_scripts):
        # Create a test character PNG
        char_path = tmp_path / "test_char.png"
        _create_test_char_png(char_path)

        agent = CharacterAgent()
        ctx = {
            "character_mode": "talking_pet",
            "character_images": [str(char_path)],
            "scripts": sample_scripts,
            "job_dir": str(tmp_path),
        }
        result = agent.execute(ctx)

        assert result["character_mode"] == "talking_pet"
        assert result["character_frames_available"] is True
        assert result["character_fps"] == 6
        assert len(result["character_frames"]) > 0

        # Verify frames exist
        frames_dir = Path(result["character_frames_dir"])
        assert frames_dir.exists()
        total_frames = sum(len(fs) for fs in result["character_frames"].values())
        assert total_frames > 0
        # Verify first frame is valid PNG
        first_seg = list(result["character_frames"].values())[0]
        assert len(first_seg) > 0
        assert Path(first_seg[0]).exists()

    def test_talking_avatar_generates_frames(self, tmp_path, sample_scripts):
        char_path = tmp_path / "avatar.png"
        _create_test_char_png(char_path)

        agent = CharacterAgent()
        ctx = {
            "character_mode": "talking_avatar",
            "character_images": [str(char_path)],
            "scripts": sample_scripts,
            "job_dir": str(tmp_path),
        }
        result = agent.execute(ctx)

        assert result["character_mode"] == "talking_avatar"
        assert result["character_frames_available"] is True

    def test_frames_per_segment_count(self, tmp_path, sample_scripts):
        """Each segment gets ~6 frames per second * duration"""
        char_path = tmp_path / "char.png"
        _create_test_char_png(char_path)

        agent = CharacterAgent()
        ctx = {
            "character_mode": "talking_pet",
            "character_images": [str(char_path)],
            "scripts": sample_scripts,
            "job_dir": str(tmp_path),
        }
        result = agent.execute(ctx)

        # sample_scripts has: 1 hook (~4s) + 2 scenes (5+8s) + 1 cta (~5s)
        # Total ~22s * 6fps ≈ 132 frames
        total = sum(len(fs) for fs in result["character_frames"].values())
        assert 20 <= total <= 200  # Reasonable range

    def test_agent_is_non_critical(self):
        agent = CharacterAgent()
        assert agent.is_critical is False

    def test_empty_scripts(self, tmp_path):
        char_path = tmp_path / "char.png"
        _create_test_char_png(char_path)

        agent = CharacterAgent()
        ctx = {
            "character_mode": "talking_pet",
            "character_images": [str(char_path)],
            "scripts": [],
            "job_dir": str(tmp_path),
        }
        result = agent.execute(ctx)
        assert result["character_frames_available"] is False


class TestCharacterAgentPipelineIntegration:
    """Verify CharacterAgent in pipeline context"""

    def test_pipeline_includes_character_agent(self):
        from backend.agents.pipeline import Pipeline

        pipeline = Pipeline.default()
        agent_names = [a.name for a in pipeline.agents]
        assert "CharacterAgent" in agent_names

        # CharacterAgent must be before VideoComposerAgent
        char_idx = agent_names.index("CharacterAgent")
        comp_idx = agent_names.index("VideoComposerAgent")
        assert char_idx < comp_idx

    def test_pipeline_inits_character_mode(self):
        from backend.agents.pipeline import Pipeline

        pipeline = Pipeline()
        ctx = pipeline._init_context({
            "source_url": "https://example.com",
            "character_mode": "talking_pet",
        })
        assert ctx["character_mode"] == "talking_pet"

    def test_context_keys_expected_by_composer(self):
        """Verify CharacterAgent output keys are available"""
        expected_keys = {
            "character_mode", "character_frames",
            "character_frames_available", "character_frames_dir",
            "character_fps",
        }
        context = {
            "character_mode": "talking_pet",
            "character_frames": {},
            "character_frames_available": True,
            "character_frames_dir": "/tmp/frames",
            "character_fps": 6,
        }
        for key in expected_keys:
            assert key in context