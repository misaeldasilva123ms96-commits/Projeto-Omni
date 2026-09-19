"""Offline regression evidence for credential checks: redirects issue no second request."""

import io
import json
import logging
import threading
import urllib.error
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from backend.python.config import provider_settings_controller as controller

SECRET = "provider-test-redirect-secret"
LOCATION_SECRET = "location-secret-sentinel"


@contextmanager
def server(status=200):
    requests = []
    settings = {"status": status, "location": None}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append((self.command, self.path, dict(self.headers)))
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            self.send_response(settings["status"])
            if settings["location"]:
                self.send_header("Location", settings["location"])
            self.end_headers()
            self.wfile.write(b'{"error":{"type":"provider-test-redirect-secret"}}')

        do_POST = do_GET

        def log_message(self, *_args):
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, kwargs={"poll_interval": 0.01})
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}", requests, settings
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)
        assert not thread.is_alive()


@pytest.fixture
def active_check(monkeypatch):
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")
    # Avoid shared circuit state; exercise the real controller and HTTP transport.
    monkeypatch.setattr(controller, "provider_health_probe_allowed", lambda *_: (True, {}))
    monkeypatch.setattr(controller, "record_provider_health", lambda *_, **kw: kw)
    client = controller.ProviderSettingsController(store=object())
    original_post = controller._http_post

    def run(provider, base):
        monkeypatch.setattr(controller, "_provider_base_url", lambda _: base)
        monkeypatch.setattr(
            controller, "_http_post",
            lambda **kw: original_post(**{**kw, "url": base + "/v1/messages"}),
        )
        return client.test_provider("redirect-test-user", provider, SECRET)

    return run


def assert_safe(result, caplog):
    serialized = json.dumps(result) + caplog.text
    for private in (SECRET, LOCATION_SECRET, "Authorization", "x-api-key", "Traceback", "127.0.0.1"):
        assert private not in serialized


@pytest.mark.parametrize("status", range(300, 400))
@pytest.mark.parametrize("provider,method,header", [
    ("openai", "GET", "Authorization"),
    ("anthropic", "POST", "X-Api-Key"),
])
def test_all_redirects_never_reach_second_server(status, provider, method, header, active_check, caplog):
    caplog.set_level(logging.DEBUG)
    with server() as (destination, second, second_settings), server(status) as (source, first, settings):
        settings["location"] = destination + "/next?token=" + LOCATION_SECRET
        # A -> B -> A would form a chain/loop if followed. Only A may be reached.
        second_settings.update(status=302, location=source + "/loop")
        result = active_check(provider, source)
        assert len(first) == 1
        assert len(second) == 0
        assert first[0][0] == method
        assert SECRET in first[0][2][header]
        assert result["success"] is False
        assert result["error"] == "redirect_denied"
        assert_safe(result, caplog)


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_same_host_loop_denied(status, provider, active_check, caplog):
    with server(status) as (source, requests, settings):
        settings["location"] = "/models?token=" + LOCATION_SECRET
        result = active_check(provider, source)
        assert len(requests) == 1
        assert result["error"] == "redirect_denied"
        assert_safe(result, caplog)


@pytest.mark.parametrize("provider", ["openai", "openrouter", "groq", "gemini", "anthropic"])
def test_success_200_preserves_provider_semantics(provider, active_check, caplog):
    with server() as (source, requests, _):
        result = active_check(provider, source)
        assert result["success"] is True
        assert len(requests) == 1
        assert_safe(result, caplog)


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
@pytest.mark.parametrize("status", [401, 403, 429, 500])
def test_http_failures_do_not_expose_response_body(provider, status, active_check, caplog):
    with server(status) as (source, requests, _):
        result = active_check(provider, source)
        assert result["success"] is False
        assert len(requests) == 1
        assert_safe(result, caplog)


@pytest.mark.parametrize("provider,transport", [("openai", "_http_get"), ("anthropic", "_http_post")])
@pytest.mark.parametrize("error", [
    urllib.error.URLError(SECRET), TimeoutError(SECRET), ConnectionError(SECRET),
    urllib.error.HTTPError("http://127.0.0.1/?token=" + SECRET, 500, SECRET, {}, io.BytesIO(SECRET.encode())),
])
def test_transport_exceptions_are_public_safe(provider, transport, error, monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)
    def fail(**kwargs):
        assert kwargs["timeout"] == 5
        raise error
    monkeypatch.setattr(controller, transport, fail)
    result = controller._run_provider_test(provider, SECRET)
    assert result["success"] is False
    assert_safe(result, caplog)


def test_unexpected_active_test_exception_does_not_log_secret(monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)
    def fail(*_args):
        raise ValueError(SECRET)
    monkeypatch.setattr(controller, "_test_openai_compatible", fail)
    result = controller._run_provider_test("openai", SECRET)
    assert result["success"] is False
    assert_safe(result, caplog)


@pytest.mark.parametrize("method", ["GET", "POST"])
def test_redirect_exception_itself_has_no_sensitive_details(method):
    with server(302) as (source, requests, settings):
        settings["location"] = source + "/?token=" + LOCATION_SECRET
        with pytest.raises(urllib.error.HTTPError) as caught:
            if method == "GET":
                controller._http_get(source, {"Authorization": SECRET})
            else:
                controller._http_post(source, {"x-api-key": SECRET}, {})
        assert len(requests) == 1
        assert caught.value.code == 302
        assert caught.value.headers is None
        for value in (str(caught.value), repr(caught.value), caught.value.url):
            assert SECRET not in value
            assert LOCATION_SECRET not in value
            assert source not in value
