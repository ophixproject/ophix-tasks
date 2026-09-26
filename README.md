# ophix-tasks

Task scheduling domain plugin for [Ophix Project](https://ophix.io) servers.

Operators define named Schedules containing task definitions. Clients are granted access at the Schedule level and receive all active tasks in a single API call. Tier 2 clients apply the task list to the host's native scheduler.

---

## Installation

```bash
pip install ophix-tasks ophix-docs venv-cmds
ophix-manage configure_install taskserver
ophix-manage run_install taskserver
sudo bash taskserver_sudo_install.sh
```

`ophix-docs` and `venv-cmds` are recommended but optional. A theme pack (e.g. `ophix-theme-midnight`) can be added for
custom branding; the built-in Ophix theme is active on fresh installs by default.

---

## Concepts

### Schedule

A named collection of tasks — the artifact clients are linked to. A host may hold access to multiple Schedules simultaneously, receiving tasks from all of them.

### Scheduler

A named target scheduling system (`cron`, `systemd`, `wts`, etc.), seeded by migration. Each Scheduler carries a validator class that checks the `interval` field is in the format that scheduler expects (a cron expression for `cron`, a systemd calendar spec for `systemd`), plus operator-facing help text explaining that format. Operators can disable a Scheduler they don't support; disabled Schedulers cannot be selected on new tasks.

Each Scheduled Task is assigned to exactly one Scheduler via its `scheduler` field. Tier 2 clients use this to pick up only the tasks meant for them — `ophix-task-crontab` applies `cron`-scheduled tasks, `ophix-task-systemd` applies `systemd`-scheduled ones.

### Scheduled Task

An individual task within a Schedule. Each task has exactly one scheduling mode:

| Field | Description |
| --- | --- |
| `scheduler` | Target scheduling system (see Scheduler above) — governs the expected `interval` format |
| `run_at` | One-off: exact date and time to execute |
| `interval` | Recurring: an expression in the format the assigned `scheduler` expects (e.g. `0 2 * * *` for cron) |

Optional time bounds enforced server-side:

| Field | Description |
| --- | --- |
| `starts_at` | Do not return this task before this date and time |
| `ends_at` | Stop returning this task after this date and time |

State flags:

| Field | Description |
| --- | --- |
| `enabled` | Disabled tasks are not returned by the server at all |
| `paused` | Paused tasks are still returned, but Tier 2 clients write them as commented-out/disabled entries rather than active ones |

Output handling controls where stdout and stderr go when the task runs:

| Field | Options |
| --- | --- |
| `stdout_handling` | `inherit` · `report` · `null` · `file` |
| `stderr_handling` | `inherit` · `report` · `null` · `merge` · `file` |
| `log_file` | Append path (used when handling is `file`) |

`description` is an optional note written as a comment above the cron entry.

A Schedule itself also has an `enabled`/`paused` pair with the same meaning, applying to every task within it.

### Client Schedule Access

Links a Client to a Schedule. Flags: `enabled` (client can read tasks from this Schedule), `can_update` (client may create tasks via the API), `can_delete` (gated by `ENABLE_ARTIFACT_DELETE` in `.env`), `paused` (pause this Schedule for this client only, without affecting other clients), `notes` (free-text operator note).

---

## API

### `GET /api/tasks/`

Returns a flat JSON array of tasks for the authenticated client across all linked Schedules. Disabled tasks are included so Tier 2 clients can write them as commented-out entries.

Optional filter: `?schedule=<name>` — restrict to a single named Schedule.

### `POST /api/tasks/`

Create a task in a Schedule. Requires `can_update` on the access record. Skips silently if a task with the same command already exists.

### `POST /api/tasks/<id>/report/`

Store execution output reported by `task-client report`. Creates a Task Execution Log entry visible in the admin.

---

## Admin

**Schedules** — primary view. Manage tasks inline, assign client access.

**Scheduled Tasks** — cross-schedule view. Filter, enable/disable, and edit tasks without opening individual Schedules.

**Task Execution Logs** — read-only log of output reported by fleet clients.

---

## Docs import

```bash
ophix-manage update_docs --include-app-docs ophix.core,ophix_tasks,ophix_docs
```
