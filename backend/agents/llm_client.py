"""
LLM Client — Clean interface cho agents gọi LLM.
Agents chỉ cần: llm.generate(prompt, system) → str
Không cần biết provider internals.
"""

import json
import logging
from typing import Optional, Union

logger = logging.getLogger("agents.llm")


class LLMClient:
    """
    Thin wrapper over LLM providers.
    Hides all provider-specific logic from agents.
    """

    def __init__(self):
        self._manager = None

    def _get_manager(self):
        """Lazy init — tránh import lúc module load"""
        if self._manager is None:
            try:
                from backend.core.llm_manager import get_llm_manager
                self._manager = get_llm_manager()
            except Exception as e:
                logger.error(f"Failed to initialize LLM manager: {e}")
                raise RuntimeError(f"LLM not available: {e}")
        return self._manager

    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        """
        Generate text from LLM.

        Args:
            prompt: User prompt
            system: Optional system prompt (prepended to prompt)

        Returns:
            Generated text string
        """
        manager = self._get_manager()
        if system:
            full_prompt = f"{system}\n\n{prompt}"
        else:
            full_prompt = prompt
        return manager.call(full_prompt)

    def generate_json(self, prompt: str, system: Optional[str] = None) -> Union[dict, list]:
        """
        Generate JSON from LLM — auto-strips markdown fences.

        Returns:
            Parsed JSON (dict or list)
        """
        text = self.generate(prompt, system)
        text = text.strip()

        # Strip markdown code fences
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0]

        return json.loads(text)


# Singleton instance
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get or create LLM client singleton"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
