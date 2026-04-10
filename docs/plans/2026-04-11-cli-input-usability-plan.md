# CLI Input Usability Plan

Date: 2026-04-11

## Goal

Improve the interactive CLI input experience so typed slash commands stay visible, drafts survive interactive prompts, external-editor editing is available, readline/vi behavior feels sane, and terminal redraws flicker less.

## User-Requested Themes

1. Commands typed in the interface should be shown instead of feeling hidden.
2. Add a shortcut that opens vi (or the user’s configured editor) to edit the current message.
3. Improve overall buffer behavior.
4. Reduce flicker.
5. Do not lose the in-progress buffer during interactions.
6. Improve readline-style editing support and command ergonomics.
7. Keep the work split into separate, focused commits.

## Additional Issues Discovered During Inspection

1. Alias collision: `/q` is registered as both `/queue` and `/quit`, and the later entry wins in `resolve_command()`. That makes command ergonomics inconsistent and surprising.
2. Modal prompt draft preservation is incomplete. `sudo` snapshots and restores the draft, but clarify/approval/secret flows do not consistently preserve in-progress input.
3. The TUI `Application(...)` does not enable an explicit editing mode, so prompt_toolkit’s richer Emacs/vi behavior is underused.
4. Slow slash commands print only a busy status like `⏳ Reloading MCP servers...`, which can obscure the exact command the user entered.
5. Several redraw paths call `invalidate()` aggressively; there is already throttling support, but some hot paths still force repaint churn.

## Relevant Files

- `cli.py`
- `hermes_cli/commands.py`
- `hermes_cli/callbacks.py`
- `tests/cli/test_cli_loading_indicator.py`
- `tests/cli/test_cli_secret_capture.py`
- `tests/hermes_cli/test_commands.py`
- New focused CLI tests as needed

## Commit Plan

### Commit 1: Make entered slash commands visible and fix command ergonomics

Scope:
- Ensure slow slash commands visibly echo the exact command the user entered before/while running.
- Keep the busy indicator, but make it additive instead of replacing the user’s command context.
- Resolve the `/q` alias collision and make short command aliases more predictable.
- Add regression coverage for command echo and alias resolution.

Acceptance:
- A slow slash command shows the exact typed command in the transcript.
- Command aliases no longer have ambiguous or shadowed behavior.

### Commit 2: Add external-editor editing shortcut and command

Scope:
- Add a prompt_toolkit keybinding for “edit current buffer in external editor”, following familiar shell/editor conventions.
- Respect `$VISUAL`, then `$EDITOR`, then fall back to `vi`.
- Preserve cursor/buffer content round-trip after editor exit.
- Add a slash command as a discoverable path if that improves usability.
- Add tests for editor resolution and buffer round-tripping at the helper level.

Acceptance:
- The current draft can be edited in vi/external editor and returns to the input field afterward.
- The feature works even when the draft spans multiple lines.

### Commit 3: Preserve drafts across modal interactions

Scope:
- Generalize modal draft snapshot/restore so clarify, approval, and secret capture do not destroy the current draft.
- Ensure cancel/timeout paths restore the original draft cleanly.
- Keep secret-entry safety: secrets should not accidentally capture stale draft text.
- Add targeted tests for restore behavior.

Acceptance:
- Starting and exiting an approval/clarify/secret prompt restores the prior draft unless the user intentionally replaced it.
- Secret prompts remain safe and do not submit stale text as secrets.

### Commit 4: Improve readline/vi editing support and input-field sanity

Scope:
- Enable explicit prompt_toolkit editing mode configuration.
- Keep sane defaults for common readline-like actions.
- Add familiar bindings where missing, especially around history/search/editor workflows.
- Make command input behavior consistent with multiline usage.
- Add/update tests around command resolution and input-mode helpers.

Acceptance:
- The input field supports a clearer, more predictable editing model.
- Vi/external-editor workflows feel first-class instead of bolted on.

### Commit 5: Reduce flicker and improve redraw/buffer stability

Scope:
- Audit forced invalidations and reduce unnecessary repaint churn.
- Avoid redundant status prints that duplicate context and cause visual jumping.
- Keep buffer state stable while agent/tool/status updates stream.
- Add or update regression coverage for slow-command/loading indicator behavior where practical.

Acceptance:
- Slow command and agent-run UI updates cause less visual churn.
- Draft text remains stable during background UI state transitions.

## Implementation Notes

- Follow CONTRIBUTING.md: keep changes focused, test manually via `hermes`, run targeted tests during development, then run the full suite before finishing.
- Use Conventional Commits.
- Prefer behavior-preserving refactors before altering visible UX.
- Be careful with cross-platform terminal/editor behavior.
- For editor launching, use prompt_toolkit-friendly terminal handoff patterns so the TUI restores cleanly.

## Test Plan

Minimum during development:
- Focused unit tests for command registry / CLI behavior
- Focused tests for modal draft preservation
- Focused tests for editor helper behavior
- Focused tests for loading-indicator / command-echo behavior

Before finishing:
- `pytest tests/cli/ -q`
- `pytest tests/hermes_cli/test_commands.py -q`
- `pytest tests/ -v`

## Manual Verification

1. Start `hermes` in the interactive CLI.
2. Type a slow slash command and verify the exact command remains visible.
3. Type a multiline draft, open the editor shortcut, save, and verify the edited content returns.
4. Start a draft, trigger clarify/approval/secret flows, then cancel/timeout/complete and verify the draft survives.
5. Exercise history, completion, queue/interrupt behavior, and multiline editing.
6. Watch for redraw flicker during spinner/status updates and long-running commands.
