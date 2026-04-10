"""Tests for CLI external-editor support."""

from unittest.mock import MagicMock, patch

from cli import HermesCLI
from hermes_cli.commands import resolve_command


class _FakeBuffer:
    def __init__(self):
        self.calls = []

    def open_in_editor(self, validate_and_handle=False):
        self.calls.append(validate_and_handle)


class _FakeApp:
    def __init__(self):
        self.current_buffer = _FakeBuffer()


def _make_cli(with_app=True):
    cli_obj = HermesCLI.__new__(HermesCLI)
    cli_obj._app = _FakeApp() if with_app else None
    cli_obj._command_running = False
    cli_obj._command_status = ""
    cli_obj._command_display = ""
    cli_obj._sudo_state = None
    cli_obj._secret_state = None
    cli_obj._approval_state = None
    cli_obj._clarify_state = None
    return cli_obj


def test_edit_alias_resolves_to_edit_command():
    assert resolve_command("vi").name == "edit"


def test_open_external_editor_uses_prompt_toolkit_buffer_editor():
    cli_obj = _make_cli()

    assert cli_obj._open_external_editor() is True
    assert cli_obj._app.current_buffer.calls == [False]


def test_open_external_editor_rejects_when_no_tui():
    cli_obj = _make_cli(with_app=False)

    with patch("cli._cprint") as mock_cprint:
        assert cli_obj._open_external_editor() is False

    assert mock_cprint.called
    assert "interactive cli" in str(mock_cprint.call_args).lower()


def test_open_external_editor_rejects_modal_prompts():
    cli_obj = _make_cli()
    cli_obj._approval_state = {"selected": 0}

    with patch("cli._cprint") as mock_cprint:
        assert cli_obj._open_external_editor() is False

    assert mock_cprint.called
    assert "active prompt" in str(mock_cprint.call_args).lower()


def test_process_command_edit_opens_editor():
    cli_obj = _make_cli()
    cli_obj.config = {}
    cli_obj.console = MagicMock()
    cli_obj.agent = None
    cli_obj.conversation_history = []

    with patch.object(cli_obj, "_open_external_editor", return_value=True) as open_editor:
        assert cli_obj.process_command("/edit") is True

    open_editor.assert_called_once_with()
