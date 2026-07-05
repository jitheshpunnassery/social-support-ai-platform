"""
Thin wrapper around a locally hosted LLM (Ollama, served through its
OpenAI-compatible /v1 endpoint). Falls back to a deterministic rule-based
responder when no local model server is reachable -- OR when it's
reachable but too slow to answer within OLLAMA_TIMEOUT_SECONDS (a cold
model load or CPU-bound generation can otherwise hang far longer than a
caller is willing to wait, since the openai SDK's default timeout is
several minutes). Bounding each call keeps total request latency
predictable even when several LLM calls happen in one pipeline run
(resume parsing, validation summary, decision explanation, enablement
narrative can all fire in a single /applications submission).
"""
import json
import logging

from openai import OpenAI, APIConnectionError, APITimeoutError

from config import settings

logger = logging.getLogger(__name__)


class LocalLLMClient:
    def __init__(self):
        self._client = OpenAI(
            base_url=settings.OLLAMA_BASE_URL,
            api_key=settings.OLLAMA_API_KEY,
            timeout=settings.OLLAMA_TIMEOUT_SECONDS,
            max_retries=0,  # fail fast -> fallback, rather than the SDK's default retry/backoff
        )
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
                    timeout=settings.OLLAMA_TIMEOUT_SECONDS,
                )
                return resp.choices[0].message.content
            except APITimeoutError:
                logger.warning("LLM call exceeded OLLAMA_TIMEOUT_SECONDS=%s; using fallback. "
                                "If Ollama is just slow (cold model load / CPU inference), raise "
                                "OLLAMA_TIMEOUT_SECONDS in .env rather than the client-side request timeout.",
                                settings.OLLAMA_TIMEOUT_SECONDS)
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
