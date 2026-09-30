# ophix-tasks

**Centralized task scheduling for your server fleet** — part of [Ophix](https://ophix.io), a modular, self-hosted fleet management platform.

If your servers have accumulated a scattered mess of forgotten cron jobs, systemd timers nobody remembers writing, and scripts nobody's sure are still needed — `ophix-tasks` gives you one place to define, audit, and manage scheduled tasks across every host, instead of SSHing into each one to find out what's actually running.

Operators define named Schedules containing task definitions in one central admin panel. Each host runs a lightweight client that pulls its assigned tasks and applies them to the host's native scheduler (cron or systemd) — so execution stays exactly where it's always lived, just no longer invisible.

---

## Installation

See [installation.md](installation.md) for the full step-by-step guide — service user, TLS setup, the guided installer, and getting the service running under nginx and systemd.

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
