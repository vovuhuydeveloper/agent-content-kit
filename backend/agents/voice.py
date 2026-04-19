"""
VoiceGeneratorAgent — Tạo voiceover TTS từ script text.
Hỗ trợ: ElevenLabs (paid), edge-tts (free fallback).
Auto-selects voice based on language.
"""

import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict

# Load .env so voice IDs are available
try:
    from dotenv import load_dotenv
    load_dotenv(override=False)
except ImportError:
    pass

from .base import BaseAgent

logger = logging.getLogger("agent.voice_generator")

# ElevenLabs voice mapping per language
# Use ELEVENLABS_VOICE_ID env var to override
ELEVENLABS_VOICES = {
    "vi": {
        "voice_id": "TX3LPaxmHKxFdv7VOQHJ",  # Liam — Energetic, Social Media Creator
        "model": "eleven_v3",
        "stability": 0.50,
        "similarity_boost": 0.75,
        "style": 0.45,
    },
    "en": {
        "voice_id": "21m00Tcm4TlvDq8ikWAM",  # Rachel
        "model": "eleven_v3",
        "stability": 0.50,
        "similarity_boost": 0.75,
        "style": 0.40,
    },
    "ja": {
        "voice_id": None,
        "model": "eleven_v3",
        "stability": 0.50,
        "similarity_boost": 0.75,
        "style": 0.40,
    },
    "ko": {
        "voice_id": None,
        "model": "eleven_v3",
        "stability": 0.50,
        "similarity_boost": 0.75,
        "style": 0.40,
    },
    "zh": {
        "voice_id": None,
        "model": "eleven_v3",
        "stability": 0.50,
        "similarity_boost": 0.75,
        "style": 0.40,
    },
}

# Edge-TTS voice mapping (free, high quality)
EDGE_TTS_VOICES = {
    "vi": "vi-VN-HoaiMyNeural",     # Vietnamese female, natural
    "en": "en-US-AriaNeural",        # English female
    "ja": "ja-JP-NanamiNeural",      # Japanese female
    "ko": "ko-KR-SunHiNeural",      # Korean female
    "zh": "zh-CN-XiaoxiaoNeural",    # Chinese female
}


class VoiceGeneratorAgent(BaseAgent):
    name = "VoiceGeneratorAgent"
    description = "Tạo voiceover từ script text (TTS)"

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        scripts = context["scripts"]
        job_dir = Path(context["job_dir"])
        language = context.get("language", "vi")

        voice_dir = job_dir / "voices"
        voice_dir.mkdir(exist_ok=True)

        voice_files = []

        for script in scripts:
            script_id = script.get("script_id", 1)

            # Ghép text từ các scenes
            full_text = self._build_voice_text(script)

            output_path = voice_dir / f"voice_{script_id}.mp3"

            # ElevenLabs v3 first, edge-tts fallback
            try:
                success = self._generate_elevenlabs(full_text, output_path, language)
            except Exception:
                success = False
            if not success:
                success = self._generate_edge_tts(full_text, output_path, language)

            if success and output_path.exists():
                voice_files.append({
                    "script_id": script_id,
                    "path": str(output_path),
                    "text": full_text,
                })
                logger.info(f"Voice {script_id} generated: {output_path.name}")
            else:
                logger.error(f"Failed to generate voice for script {script_id}")

        return {
            "voice_files": voice_files,
            "voice_count": len(voice_files),
        }

    def _build_voice_text(self, script: Dict) -> str:
        """Build voice text with expressive audio tags for ElevenLabs v3"""
        parts = []

        if script.get("hook"):
            parts.append(f"[excited] {script['hook']}")

        for scene in script.get("scenes", []):
            if scene.get("text"):
                parts.append(scene["text"])

        if script.get("cta"):
            parts.append(f"[happy] {script['cta']}")

        return " ".join(parts)

    def _get_elevenlabs_voice_id(self, language: str) -> str:
        """Get the best voice ID for a language"""
        # Priority: language-specific env var → general env var → config default
        lang_key = f"ELEVENLABS_VOICE_ID_{language.upper()}"
        voice_id = os.getenv(lang_key, "")

        if not voice_id:
            voice_id = os.getenv("ELEVENLABS_VOICE_ID", "")

        if not voice_id:
            config = ELEVENLABS_VOICES.get(language, ELEVENLABS_VOICES["en"])
            voice_id = config.get("voice_id", "")

        if not voice_id:
            # Default: Rachel (works well with multilingual_v2 for all languages)
            voice_id = "21m00Tcm4TlvDq8ikWAM"

        return voice_id

    def _generate_elevenlabs(self, text: str, output_path: Path, language: str) -> bool:
        """Generate voice using ElevenLabs API with language-specific settings"""
        api_key = os.getenv("ELEVENLABS_API_KEY", "")
        if not api_key:
            logger.debug("ElevenLabs API key not set")
            return False

        voice_id = self._get_elevenlabs_voice_id(language)
        config = ELEVENLABS_VOICES.get(language, ELEVENLABS_VOICES["en"])

        try:
            import requests

            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": api_key,
            }
            data = {
                "text": text,
                "model_id": config["model"],
                "voice_settings": {
                    "stability": config["stability"],
                    "similarity_boost": config["similarity_boost"],
                    "style": config.get("style", 0.5),
                    "use_speaker_boost": True,
                }
            }

            resp = requests.post(url, json=data, headers=headers, timeout=60)
            if resp.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                logger.info(f"ElevenLabs voice generated ({language}, voice={voice_id[:12]}...)")
                return True
            else:
                logger.warning(f"ElevenLabs error {resp.status_code}: {resp.text[:200]}")
                return False
        except Exception as e:
            logger.warning(f"ElevenLabs failed: {e}")
            return False

    def _generate_edge_tts(self, text: str, output_path: Path, language: str) -> bool:
        """Generate voice using edge-tts (free, Microsoft)"""
        voice = EDGE_TTS_VOICES.get(language, EDGE_TTS_VOICES["vi"])

        try:
            # edge-tts CLI
            cmd = [
                "edge-tts",
                "--voice", voice,
                "--text", text,
                "--write-media", str(output_path),
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0 and output_path.exists():
                logger.info(f"edge-tts voice generated with {voice}")
                return True
            else:
                logger.warning(f"edge-tts failed: {result.stderr[:200]}")
                return False
        except FileNotFoundError:
            logger.warning("edge-tts not installed. Install: pip install edge-tts")
            return False
        except Exception as e:
            logger.warning(f"edge-tts error: {e}")
            return False
