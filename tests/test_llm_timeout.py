"""Verifies the Ollama timeout fix actually bounds latency: a deliberately
slow fake OpenAI-compatible server (sleeps longer than OLLAMA_TIMEOUT_SECONDS
before responding) must cause LocalLLMClient.chat() to fall back to the
deterministic response within roughly OLLAMA_TIMEOUT_SECONDS, not hang
indefinitely waiting for the slow server."""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest


class _SlowOllamaHandler(BaseHTTPRequestHandler):
    """Responds to /models instantly (so _probe() thinks the server is up)
    but sleeps well past the configured timeout on /chat/completions."""

    def log_message(self, *args):  # silence default request logging
        pass

    def do_GET(self):
        if self.path.endswith("/models"):
            self._send_json({"data": []})
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if "/chat/completions" in self.path:
            time.sleep(5)  # deliberately longer than the test's timeout setting (2s)
            self._send_json({"choices": [{"message": {"content": "too slow, should not see this"}}]})
        else:
            self.send_response(404)
            self.end_headers()

    def _send_json(self, payload):
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture(scope="module")
def slow_ollama_server():
    server = HTTPServer(("localhost", 0), _SlowOllamaHandler)
    port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield port
    server.shutdown()


def test_slow_llm_falls_back_within_timeout_budget(slow_ollama_server, monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", f"http://localhost:{slow_ollama_server}/v1")
    monkeypatch.setenv("OLLAMA_TIMEOUT_SECONDS", "2")

    # Re-import fresh so the new env vars are picked up by config.settings
    import importlib
    import config
    importlib.reload(config)
    import agents.llm_client as llm_client_module
    importlib.reload(llm_client_module)

    client = llm_client_module.LocalLLMClient()

    start = time.perf_counter()
    result = client.chat("system prompt", "user prompt")
    elapsed = time.perf_counter() - start

    assert "too slow" not in result, "Should have timed out before the slow server responded"
    assert "offline fallback" in result or "fallback" in result.lower()
    # Should return well before the server's 5s sleep completes -- bounded
    # by OLLAMA_TIMEOUT_SECONDS (2s) plus a small margin, not 5+ seconds.
    assert elapsed < 4.5, f"Expected a fast fallback (<4.5s), took {elapsed:.2f}s -- timeout isn't being enforced"
