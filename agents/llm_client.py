"""
Thin wrapper around a locally hosted LLM (Ollama, served through its
OpenAI-compatible /v1 endpoint). Falls back to a deterministic rule-based
responder when no local model server is reachable, so the rest of the
pipeline (orchestration, DB writes, UI) is fully demoable offline/in CI.
"""
import json
import logging

from openai import OpenAI, APIConnectionError

from config import settings

logger = logging.getLogger(__name__)


class LocalLLMClient:
    def __init__(self):
        self._client = OpenAI(base_url=settings.OLLAMA_BASE_URL, api_key=settings.OLLAMA_API_KEY)
        self._available = None  # lazily probed

    def _probe(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            self._client.models.list()
            self._available = True
        except Exception as e:  # noqa: BLE001
            logger.warning("Local LLM (Ollama) unreachable at %s (%s). Using rule-based fallback.",
                            settings.OLLAMA_BASE_URL, e)
            self._available = False
        return self._available

    def chat(self, system: str, user: str, json_mode: bool = False, model: str | None = None) -> str:
        if self._probe():
            try:
                resp = self._client.chat.completions.create(
                    model=model or settings.OLLAMA_MODEL,
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                    temperature=0.1,
                    response_format={"type": "json_object"} if json_mode else None,
                )
                return resp.choices[0].message.content
            except (APIConnectionError, Exception) as e:  # noqa: BLE001
                logger.warning("LLM call failed (%s); using fallback.", e)
        return self._fallback(system, user, json_mode)

    @staticmethod
    def _fallback(system: str, user: str, json_mode: bool) -> str:
        """Deterministic stand-in used only when Ollama isn't running. Real
        deployments always hit the local model; this keeps the agent
        contracts (structured JSON in/out) identical either way."""
        if json_mode:
            return json.dumps({
                "note": "LLM offline - deterministic fallback used",
                "reasoning": "Rule-based extraction/validation applied instead of generative reasoning.",
            })
        return ("[offline fallback] Local LLM server not reachable at the configured OLLAMA_BASE_URL. "
                "Start Ollama (see README) to enable full generative reasoning; deterministic "
                "rule-based logic was used for this step instead.")


llm_client = LocalLLMClient()
