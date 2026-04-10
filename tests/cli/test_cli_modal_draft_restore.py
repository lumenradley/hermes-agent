"""Regression tests for preserving input drafts across modal prompts."""

import threading
import time
from unittest.mock import patch

from cli import HermesCLI
from hermes_cli.callbacks import prompt_for_secret


class _FakeBuffer:
    def __init__(self, text="draft text", cursor_position=None):
        self.text = text
        self.cursor_position = len(text) if cursor_position is None else cursor_position

    def reset(self, append_to_history=False):
        self.text = ""
        self.cursor_position = 0


class _FakeApp:
    def __init__(self, text="draft text"):
        self.current_buffer = _FakeBuffer(text=text)
        self.invalidated = 0

    def invalidate(self):
        self.invalidated += 1


def _make_cli(text="draft text"):
    cli_obj = HermesCLI.__new__(HermesCLI)
    cli_obj._app = _FakeApp(text=text)
    cli_obj._last_invalidate = 0.0
    cli_obj._modal_input_snapshot = None
    cli_obj._clarify_state = None
    cli_obj._clarify_deadline = 0
    cli_obj._clarify_freetext = False
    cli_obj._approval_state = None
    cli_obj._approval_deadline = 0
    cli_obj._approval_lock = threading.Lock()
    cli_obj._secret_state = None
    cli_obj._secret_deadline = 0
    cli_obj._invalidate = lambda *args, **kwargs: None
    return cli_obj


def test_clarify_callback_restores_existing_draft_after_response():
    cli_obj = _make_cli(text="keep this draft")
    results = []

    thread = threading.Thread(
        target=lambda: results.append(cli_obj._clarify_callback("Pick one", ["A", "B"]))
    )
    thread.start()

    deadline = time.time() + 2
    while cli_obj._clarify_state is None and time.time() < deadline:
        time.sleep(0.01)

    assert cli_obj._clarify_state is not None
    assert cli_obj._app.current_buffer.text == ""

    cli_obj._clarify_state["response_queue"].put("A")
    thread.join(timeout=2)

    assert results == ["A"]
    assert cli_obj._app.current_buffer.text == "keep this draft"
    assert cli_obj._app.current_buffer.cursor_position == len("keep this draft")


def test_approval_callback_restores_existing_draft_after_response():
    cli_obj = _make_cli(text="dangerous draft")
    results = []

    thread = threading.Thread(
        target=lambda: results.append(cli_obj._approval_callback("rm -rf /tmp/demo", "demo"))
    )
    thread.start()

    deadline = time.time() + 2
    while cli_obj._approval_state is None and time.time() < deadline:
        time.sleep(0.01)

    assert cli_obj._approval_state is not None
    assert cli_obj._app.current_buffer.text == ""

    cli_obj._approval_state["response_queue"].put("deny")
    thread.join(timeout=2)

    assert results == ["deny"]
    assert cli_obj._app.current_buffer.text == "dangerous draft"
    assert cli_obj._app.current_buffer.cursor_position == len("dangerous draft")


def test_secret_prompt_restores_existing_draft_after_submit():
    cli_obj = _make_cli(text="api draft")
    results = []

    def run_prompt():
        with patch("hermes_cli.callbacks.save_env_value_secure") as save_secret:
            save_secret.return_value = {
                "success": True,
                "stored_as": "TENOR_API_KEY",
                "validated": False,
            }
            results.append(prompt_for_secret(cli_obj, "TENOR_API_KEY", "Tenor API key"))

    thread = threading.Thread(target=run_prompt)
    thread.start()

    deadline = time.time() + 2
    while cli_obj._secret_state is None and time.time() < deadline:
        time.sleep(0.01)

    assert cli_obj._secret_state is not None
    assert cli_obj._app.current_buffer.text == ""

    cli_obj._submit_secret_response("super-secret")
    thread.join(timeout=2)

    assert results[0]["success"] is True
    assert results[0]["skipped"] is False
    assert cli_obj._app.current_buffer.text == "api draft"
    assert cli_obj._app.current_buffer.cursor_position == len("api draft")
