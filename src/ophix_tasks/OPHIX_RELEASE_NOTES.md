# Ophix Tasks Release Notes

## 2026.06.05.01

- `export_tasks`: export file now includes a `meta` block with `created_at`, `server_name`, `server_version`, `hostname`, `domain`, `command`, `run_by`, `login_user`, and `ssh_origin`.

## 2026.06.02.01

- `TaskExecutionLogAdmin` now applies `DeleteRedirectToChangelistMixin` — deleting an execution log entry returns to the log list instead of the admin home page.

## 2026.05.31.01

- Added Compact/Full toggle button to the Scheduled Tasks list view. Compact mode
  hides the `description`, `stdout handling`, and `stderr handling` columns to reduce
  table width on standard desktop screens. Preference is saved in `localStorage` and
  persists across page loads.

## 2026.05.30.01

- Added `export_tasks` management command — exports Schedule and ScheduledTask
  records to JSON. Execution logs are not included. Use `--include-client-links`
  to also export ClientScheduleAccess join records.
- Added `import_tasks` management command — imports from an `export_tasks` file.
  Idempotent (schedules matched by name, tasks matched by name within their
  schedule). Tasks absent from the file are left untouched — import is additive
  only. Scheduler types resolved by name (must exist via migrate).
  `--include-client-links` imports join records including the task-domain
  `paused` flag. Supports `--dry-run` and `--quiet`.
- Added inline documentation page "Task Schedule Backup and Migration".

## 2026.05.26.01

- Update inline documentation

## 2026.05.22.01

- `prune_task_logs` now accepts `--quiet` to suppress all output, making it
  safe to run from cron without generating noise in the mail spool. `--dry-run`
  output is always shown regardless of `--quiet`.

## 2026.05.21.02

- `prune_task_logs` now reads its default retention period from the
  `PRUNE_TASK_LOG_DAYS` setting (configurable in `.env`). Falls back to
  90 days if not set. `--days` on the command line always takes precedence.

## 2026.05.21.01

- Task duplication: open any task and click **Save as new** to create a copy with all fields pre-filled for editing.

## 2026.05.14.01

- Added `OPHIX_RELEASE_NOTES.md` for release notes delivery.
