# Ophix Tasks Release Notes

## 2026.10.07.01

- Added `get_doc_tokens()` hook, discovered by `ophix-docs` (if installed) for
  `{{ token }}` substitution in shared markdown. Contributes `client_package`
  (`ophix-task-client`) and `client_command` (`task-client`) so the generic
  Client Quickstart doc in `ophix-server-base` can render this domain's correct
  example instead of staying generic.

## 2026.10.04.01

- Added `installation.md` — a full production-style install walkthrough (dedicated service
  user, venv, TLS via `ophix-ca-tools`, the guided `configure_install`/`run_install` steps,
  nginx/systemd integration) alongside the existing quick-install README. Verified against a
  real live taskserver install on `ipc2` this session, and corrected as real gaps surfaced
  during that walkthrough: the explicit `ophix-dbengine-mariadb` install step (no engine is
  bundled by default), the engine auto-select wording, a "what versions do I already have"
  check block for Prerequisites, and a reminder in Next steps to confirm DNS actually resolves
  to the host before expecting the admin UI to be reachable.
- Reworked `README.md`'s opening with a hook-first pitch, and linked its Installation section
  to `installation.md` instead of duplicating the install steps.

## 2026.09.26.04

- i18n: wrapped the fleet-API JSON error strings in `views.py` (`"Not found."`, `"Unknown scheduler: ..."`) that were previously left unwrapped to match a sibling-domain convention. Reconsidered after confirming every known Tier 1 client (`ophix-client-core`'s shared commands, `ophix-task-client`'s `core.py`) branches purely on HTTP status code and only ever *displays* the JSON body text to the operator, never parses it for control flow — so translating it is safe and has no client-compatibility risk.

## 2026.09.26.03

- i18n regression check: `STDOUT_CHOICES`/`STDERR_CHOICES`/`STREAM_CHOICES` in `models.py` render as admin dropdown/list labels but their strings were unwrapped, unlike every other field in the same file. Wrapped in `gettext_lazy`.

## 2026.09.26.02

- Verified real compatibility under Python 3.14 (not just added the classifier) as part of the taskserver-release-wave compatibility sweep, and added `Programming Language :: Python :: 3.14` to the package classifiers.

## 2026.09.26.01

- Docs: README.md and task-scheduling.md never documented the `Scheduler`
  model/`scheduler` field at all (a real, migration-seeded concept that
  determines the expected `interval` format and is how Tier 2 clients know
  which tasks are theirs), even though task-backup.md already covered it for
  export/import. Added a Scheduler concept section to both, updated field
  tables and JSON examples, and documented the task-level `paused` flag
  (previously only explained in task-crontab.md) and the full
  `ClientScheduleAccess` permission flag set (`can_delete`, `paused`, `notes`
  were missing).
- Docs: task-client.md corrected to match `ophix-task-client`'s own README fix
  — `get_tasks()`/`create_task()` signatures were missing `scheduler`
  entirely, and the "disabled tasks are included" claim was backwards
  (disabled tasks are excluded from the API response outright; `paused` tasks
  are the ones still returned for Tier 2 clients to write as inactive
  entries).

## 2026.08.30.02

- Fixed `2026.08.30.01`'s disabled-link colour change dropping the italic
  style — it should be kept alongside the new colour and weight, not
  replaced. `_DISABLED_STYLE`-equivalent spans now read
  `var(--admin-interface-disabled-color); font-weight: 600; font-style:
  italic`.

## 2026.08.30.01

- Disabled-client/disabled-schedule styling in the "Authorised Schedules"
  (Client admin) and "Authorised Clients" (Schedule admin) linked-artifact
  columns changed from an italic red-tinted mix
  (`color-mix(..., var(--admin-interface-delete-button-background-color) ...)`)
  to the theme's dedicated disabled colour at a heavier weight
  (`var(--admin-interface-disabled-color); font-weight: 600`), matching the
  same treatment applied fleet-wide to changelist disabled rows.

## 2026.08.29.03

- Fixed Description/Command textareas rendering wider than intended on `ScheduledTask`'s
  change form — two compounding causes, both predating this session's Django 6.1 CSS
  work entirely. `formfield_overrides` uses a plain `forms.Textarea(attrs={"rows": 3,
  "cols": 100})` — not Django's own `AdminTextareaWidget` — so it never got the
  `vLargeTextField` CSS class that normally caps a textarea's width; `cols=100` alone
  gives the browser a huge intrinsic size with no ceiling. `admin.css` had a
  `.form-row textarea { width: 125% }` rule ("25% wider than default") compensating
  for this, tuned against the container's width at the time it was written — once
  this session's other fixes changed that baseline width, 125% of it computed to
  something oversized instead. Fixed by removing the percentage hack from `admin.css`
  entirely and setting an explicit `"style": "width: 1240px;"` directly on the widget
  in `admin.py`, sized to comfortably fit a long rsync-style command after subtracting
  the nav sidebar and label column from a 1920px-wide screen. An inline style always
  wins over any external stylesheet rule regardless of specificity, so there's no
  interaction to manage between the two fixes. The identical unbounded-textarea
  pattern also exists in `ScheduleTaskInline`/`ClientScheduleAccessInline`
  (`cols=120`) and one other spot (`cols=80`) in this file — left alone for now since
  only the ScheduledTask form was in scope, flagged for later if wanted there too.

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
