"""Tests for CLI editing-mode detection."""

from unittest.mock import patch

from prompt_toolkit.enums import EditingMode

from cli import HermesCLI


def _make_cli():
    return HermesCLI.__new__(HermesCLI)


def test_preferred_editing_mode_defaults_to_emacs():
    cli_obj = _make_cli()

    with patch.dict("os.environ", {"VISUAL": "", "EDITOR": ""}, clear=False):
        assert cli_obj._preferred_editing_mode() == EditingMode.EMACS


def test_preferred_editing_mode_prefers_vi_family_editors():
    cli_obj = _make_cli()

    with patch.dict("os.environ", {"EDITOR": "nvim -f"}, clear=False):
        assert cli_obj._preferred_editing_mode() == EditingMode.VI


def test_preferred_editing_mode_uses_visual_before_editor():
    cli_obj = _make_cli()

    with patch.dict("os.environ", {"VISUAL": "vim", "EDITOR": "emacs"}, clear=False):
        assert cli_obj._preferred_editing_mode() == EditingMode.VI
