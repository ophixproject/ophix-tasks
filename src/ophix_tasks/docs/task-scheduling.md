---
title: Task Scheduling
slug: task-scheduling
order: 100
section: Task Scheduling
---

ophix-tasks is the Ophix server domain for distributing scheduled tasks across a fleet. Operators define named Schedules containing individual task definitions. Clients are granted access at the Schedule level and receive all tasks in a single API call. Tier 2 clients apply the task list to the host's native scheduler.

---

## Concepts

### Schedules

A **Schedule** is a named collection of tasks — the artifact that clients are granted access to. A Schedule might be `server-maintenance` (nightly jobs), `www-data-tasks` (web server cleanup under a non-root user), or `one-off-migration` (a set of tasks running during a deployment window).

Clients are linked to Schedules via the **Client Schedule Access** join record. A client may hold access to multiple Schedules simultaneously, receiving tasks from all of them. Disabling a Schedule, Client, Host, or access record all prevent task delivery.

### Scheduled Tasks

A **Scheduled Task** is one entry within a Schedule. It defines what to run and when.

**Scheduling:** Exactly one of `run_at` or `interval` must be set:

| Field | Description |
| --- | --- |
| `run_at` | One-off: the exact date and time to execute (server timezone) |
| `interval` | Recurring: a standard cron expression, e.g. `0 2 * * *` |

**Time bounds:** Optional server-side window filters:

| Field | Description |
| --- | --- |
| `starts_at` | Do not return this task before this date and time |
| `ends_at` | Stop returning this task after this date and time |

The server enforces these windows in the API response — the client does not need to evaluate them.

**Output handling:** Controls where stdout and stderr go when the task runs:

| Field | Options |
| --- | --- |
| `stdout_handling` | `inherit` (cron default), `report` (send to server), `null` (/dev/null), `file` (append to log file) |
| `stderr_handling` | `inherit`, `report`, `null`, `merge` (2>&1 to stdout), `file` |
| `log_file` | Filesystem path used when either handling is set to `file` |

**Description:** Optional free-text note written as a comment line above the cron entry in the generated file.

### Client Schedule Access

The join record linking a Client to a Schedule. Permission flags:

| Flag | Description |
| --- | --- |
| `enabled` | Client receives tasks from this Schedule |
| `can_update` | Client may create tasks within this Schedule via the API |

A client may hold access to multiple enabled Schedules at the same time. There is no server-enforced limit — the operator manages which Schedules each client syncs by configuring the Tier 2 client (e.g. `task-crontab sync --schedule <name>`).

### Task Execution Log

When a task's output handling is set to `report`, the Tier 1 client pipes stdout (or stderr) into `task-client report <id>` which POSTs the output to the server. The server stores each report as a **Task Execution Log** entry linked to the task and client. View logs at **Task Scheduling → Task Execution Logs** in the admin.

---

## Admin Setup

### 1. Create a Schedule

Go to **Task Scheduling → Schedules → Add Schedule**. Give it a name (e.g. `server-maintenance`) and an optional description.

Add tasks in the **Scheduled Tasks** inline on the Schedule. Group your fields:

- **Identity:** name, enabled flag, description
- **Schedule:** run_at or interval, optional starts_at and ends_at
- **Output handling:** stdout_handling, stderr_handling, log_file

### 2. Grant Client Access

On the Schedule or on the Client, expand the **Client Schedule Access** inline and add a link. Enable `can_update` if the client should be able to create tasks via the import workflow (`task-crontab import`).

### 3. Manage Tasks

Two admin views are provided:

**Schedules** — primary view. Expand a Schedule to manage all its tasks inline and to add/remove client links.

**Scheduled Tasks** — cross-schedule view. Filter by schedule, enabled state, or output handling. Use this when you need to work across many tasks without opening individual Schedules.

---

## API Endpoints

### Fetch Tasks

```http
GET /api/tasks/
Authorization: Token <client_token>
```

Returns a flat JSON array of all tasks the client has access to, across all enabled linked Schedules. Time-bounded tasks outside their window are excluded.

**Optional filter:**

```http
GET /api/tasks/?schedule=server-maintenance
```

Returns only tasks belonging to the named Schedule.

**Response:**

```json
[
  {
    "id": 1,
    "schedule": "server-maintenance",
    "name": "nightly-backup",
    "command": "/opt/backup.sh",
    "description": "Runs the nightly backup script",
    "run_at": null,
    "interval": "0 2 * * *",
    "starts_at": null,
    "ends_at": null,
    "enabled": true,
    "stdout_handling": "report",
    "stderr_handling": "merge",
    "log_file": ""
  }
]
```

Disabled tasks (`enabled=false`) are included so Tier 2 clients can write them as commented-out entries rather than silently removing them.

### Create Task

```http
POST /api/tasks/
Authorization: Token <client_token>
Content-Type: application/json
```

Creates a task in the named Schedule. Requires `can_update` on the access record. If a task with the same command already exists (enabled or disabled), the server skips creation.

**Request:**

```json
{
  "schedule": "server-maintenance",
  "name": "nightly-backup",
  "command": "/opt/backup.sh",
  "description": "Runs the nightly backup script",
  "interval": "0 2 * * *",
  "stdout_handling": "report",
  "stderr_handling": "merge"
}
```

**Response (201):**

```json
{"status": "created", "id": 1}
```

**Response (200, already exists):**

```json
{"status": "skipped", "id": 1}
```

### Report Task Output

```http
POST /api/tasks/<id>/report/
Authorization: Token <client_token>
Content-Type: application/json
```

Store execution output for a task. Called by `task-client report` which is piped from the task command when `stdout_handling` or `stderr_handling` is set to `report`.

**Request:**

```json
{"output": "Backup completed. 42 files archived.\n"}
```

**Response (200):**

```json
{"status": "ok"}
```

---

## Settings

| Setting | Default | Description |
| --- | --- | --- |
| `SHOW_CLIENT_ARTIFACT_MODEL` | `False` | Show the Client Schedule Access model in admin |

Set in `.env`. All other behaviour is managed via the admin UI.

---

## Server Setup

```bash
pip install ophix-tasks ophix-server-base ophix-docs
ophix-manage configure_install taskserver
ophix-manage run_install taskserver
sudo bash taskserver_sudo_install.sh
```

Import docs after installation:

```bash
ophix-manage ophix_docs_update --include-app-docs ophix.core,ophix_tasks,ophix_docs,ophix_theme_tools
```
