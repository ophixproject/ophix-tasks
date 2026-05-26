# ophix-tasks

Task scheduling domain plugin for [Ophix Project](https://ophix.io) servers.

Operators define named Schedules containing task definitions. Clients are granted access at the Schedule level and receive all active tasks in a single API call. Tier 2 clients apply the task list to the host's native scheduler.

---

## Installation

```bash
pip install ophix-tasks ophix-server-base ophix-docs
ophix-manage configure_install taskserver
ophix-manage run_install taskserver
sudo bash taskserver_sudo_install.sh
```

---

## Concepts

### Schedule

A named collection of tasks — the artifact clients are linked to. A host may hold access to multiple Schedules simultaneously, receiving tasks from all of them.

### Scheduled Task

An individual task within a Schedule. Each task has exactly one scheduling mode:

| Field | Description |
| --- | --- |
| `run_at` | One-off: exact date and time to execute |
| `interval` | Recurring: cron expression (e.g. `0 2 * * *`) |

Optional time bounds enforced server-side:

| Field | Description |
| --- | --- |
| `starts_at` | Do not return this task before this date and time |
| `ends_at` | Stop returning this task after this date and time |

Output handling controls where stdout and stderr go when the task runs:

| Field | Options |
| --- | --- |
| `stdout_handling` | `inherit` · `report` · `null` · `file` |
| `stderr_handling` | `inherit` · `report` · `null` · `merge` · `file` |
| `log_file` | Append path (used when handling is `file`) |

`description` is an optional note written as a comment above the cron entry.

### Client Schedule Access

Links a Client to a Schedule. Flags: `enabled`, `can_update` (allows the client to create tasks via the API).

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
ophix-manage ophix_docs_update --include-app-docs ophix.core,ophix_tasks,ophix_docs,ophix_theme_tools
```
