# Ophix Tasks Release Notes

## 2026.08.29.02

- Fixed `2026.08.29.01`'s Select2 change-event fix not actually working — it checked
  `window.jQuery`, which is always `undefined`. Django deliberately does not expose
  jQuery as a plain global: `jquery.init.js` calls `jQuery.noConflict(true)`, which
  strips both `window.$` and `window.jQuery` and re-exposes jQuery only as
  `window.django.jQuery`. Since the check silently failed, both fixes fell straight
  back to the same broken `addEventListener('change', ...)` path as before — no
  error, no console output, matching the reported symptom exactly ("no response and
  nothing on the console"). Confirmed the correct reference by reading
  `select2-init.js` and `dropdown-filter.js` directly (both already use
  `window.django && window.django.jQuery`) rather than re-guessing. Both
  `initIntervalHelp()` and `initOutputWarning()` now use the same reference.

## 2026.08.29.01

- Fixed the Interval field's scheduler-dependent help text not updating when the
  Scheduler dropdown was changed through the UI. `#id_scheduler` is an FK `<select>`
  inside `.related-widget-wrapper`, so `ophix-admin-interface`'s `select2-init.js`
  auto-upgrades it to Select2 (it isn't in `autocomplete_fields`). Select2 reports a
  selection change purely via jQuery's `.trigger('change')` — there's no native
  `.change()` method on a `<select>` for jQuery to invoke as a fallback, so nothing
  dispatches a real DOM event, and `admin.js`'s `initIntervalHelp()` (bound via plain
  `addEventListener('change', ...)`) never fired. Same root cause as the `#52` filter
  dropdown bug documented for `ophix-admin-interface`, just hit independently here.
  Fixed by binding through jQuery's `.on('change', ...)` when jQuery is present
  (still catches genuine native events too), falling back to `addEventListener` only
  if jQuery isn't loaded at all.
- Found and fixed the identical bug in `initOutputWarning()` in the same file, while
  checking for other instances of the same pattern: `stdout_handling`/
  `stderr_handling` are also forced onto `Select2Widget` by
  `ScheduledTaskAdmin.formfield_for_choice_field`, so the "stdout=file has no effect
  when stderr=report" warning wasn't showing or hiding correctly when those
  dropdowns were changed via Select2's UI either. Same jQuery `.on('change', ...)`
  fix applied to both.

## 2026.08.04.01

- `export_tasks` gains a `--stable` flag: omits the `meta` block and passes `sort_keys=True`,
  so re-exporting unchanged data produces byte-identical output. Written for
  `ophix-revisions`.
- Fixed a latent nondeterminism bug in `--include-client-links`: the nested
  `client_access` join query had no explicit `.order_by()`. Now ordered by
  `client__host__name, client__name`.
- `ophix_tasks` gains `get_revisions_targets()`, declaring its own `tasks` target for
  `ophix-revisions` (if installed) to discover at runtime — no separate registration
  needed anywhere else.

## 2026.06.09.04

- Fixed `export_clients --passphrase` shown in the restore workflow — client tokens are
  stored as SHA-256 hashes and `export_clients` does not accept or require a passphrase.
- Added "Scheduled backups" section to `task-backup.md` with recommended `.env` values.

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
