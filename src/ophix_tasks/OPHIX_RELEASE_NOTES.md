# Ophix Tasks Release Notes

## Unreleased

- `prune_task_logs` now reads its default retention period from the
  `PRUNE_TASK_LOG_DAYS` setting (configurable in `.env`). Falls back to
  90 days if not set. `--days` on the command line always takes precedence.

## 2026.05.21.01

- Task duplication: open any task and click **Save as new** to create a copy with all fields pre-filled for editing.

## 2026.05.14.01

- Added `OPHIX_RELEASE_NOTES.md` for release notes delivery.
