---
title: task-client Reference
slug: task-client
order: 110
section: Task Scheduling
---

# task-client Reference

`ophix-task-client` is the Tier 1 client for the task scheduling domain. It handles authentication with the task server, provides `get_tasks()` and `create_task()` as importable functions for Tier 2 clients, and exposes the `task-client` CLI for bootstrapping and diagnostics.

---

## Installation

```bash
pip install ophix-task-client
```

---

## Configuration file: `.task.env`

| Variable | Description |
| --- | --- |
| `TASKSERVER_URL` | Task server base URL |
| `TASKSERVER_API_TOKEN` | 64-character hex client token |
| `TASKSERVER_CA_CERT` | Path to CA certificate PEM (optional — omit to use the system trust store) |

---

## Quickstart

```bash
task-client quickstart https://tasks.example.com myhost-tasks
```

This single command sets the server URL, downloads the CA certificate, and registers the client. The token is saved to `.task.env` automatically.

---

## Commands

### `quickstart <server_url> <client_name>`

Bootstrap in one step: set server URL, download CA cert, register.

```bash
task-client quickstart https://tasks.example.com myhost-tasks
```

### `register <name>`

Register this client with the task server. Run after `set server` and `download ca-cert` if bootstrapping step by step.

```bash
task-client register myhost-tasks
```

### `set server <value>`

Write the server URL to `.task.env`.

```bash
task-client set server https://tasks.example.com
```

### `download ca-cert`

Download and save the server CA certificate (TLS verification disabled for this step only).

```bash
task-client download ca-cert
```

### `rotate-token`

Generate a new token, send it to the server, and update `.task.env` on success.

```bash
task-client rotate-token
```

### `fetch`

Fetch and print the active task list as JSON. Useful for debugging.

```bash
task-client fetch
```

### `create-task`

Create a task on the server. The client must have `can_update` access to the Schedule.

```bash
task-client create-task \
  --schedule server-maintenance \
  --name nightly-backup \
  --command "/opt/backup.sh" \
  --description "Nightly backup" \
  --interval "0 2 * * *" \
  --stdout-handling report \
  --stderr-handling merge
```

| Argument | Required | Description |
| --- | --- | --- |
| `--schedule` | Yes | Schedule name to add the task to |
| `--name` | Yes | Task name |
| `--command` | Yes | Command to execute |
| `--description` | No | Comment written above the cron entry |
| `--interval` | No | Cron expression for recurring tasks |
| `--run-at` | No | ISO datetime for a one-off task |
| `--stdout-handling` | No | `inherit` (default), `report`, `null`, `file` |
| `--stderr-handling` | No | `inherit` (default), `report`, `null`, `merge`, `file` |
| `--log-file` | No | Log file path (used with `--stdout-handling=file` or `--stderr-handling=file`) |

If a task with the same command already exists in the Schedule (enabled or disabled), the server skips creation.

### `report <task_id>`

Read stdin and post it to the server as execution output for the given task. This command is normally invoked by the crontab via a pipe, not called directly.

```bash
# Generated crontab line (report stdout):
0 2 * * * root /opt/backup.sh | task-client report 1

# Generated crontab line (report stderr only):
0 2 * * * root /opt/backup.sh 2>&1 1>/dev/null | task-client report 1
```

Failures are silently ignored — the task ran; reporting is best-effort.

### `info`

Show the current configuration summary.

```bash
task-client info
```

### `doctor`

Diagnose local configuration and server connectivity.

```bash
task-client doctor
```

---

## Library API (for Tier 2 clients)

Import from `task_client.core`:

```python
from task_client.core import get_tasks, create_task
```

### `get_tasks(schedule=None, server_url=None, api_token=None, ca_cert=None)`

Fetch the task list from the task server. Returns a list of task dicts.

```python
# All tasks across all linked schedules
tasks = get_tasks()

# Tasks for a specific named schedule only
tasks = get_tasks(schedule="server-maintenance")
```

Each task dict contains:

| Field | Type | Description |
| --- | --- | --- |
| `id` | int | Task ID (used for `task-client report`) |
| `schedule` | str | Schedule name |
| `name` | str | Task name |
| `command` | str | Command to execute |
| `description` | str | Optional comment text |
| `run_at` | str or null | ISO datetime for one-off tasks |
| `interval` | str | Cron expression for recurring tasks |
| `starts_at` | str or null | Active window start |
| `ends_at` | str or null | Active window end |
| `enabled` | bool | Whether the task is enabled (disabled tasks are included for Tier 2 clients to comment out) |
| `stdout_handling` | str | `inherit`, `report`, `null`, or `file` |
| `stderr_handling` | str | `inherit`, `report`, `null`, `merge`, or `file` |
| `log_file` | str | Log file path (empty string if not set) |

Configuration is read from `.task.env` automatically. Pass explicit `server_url`, `api_token`, and `ca_cert` arguments to override.

### `create_task(schedule, name, command, ...)`

Create a task on the server. Returns `{"status": "created"|"skipped", "id": <int>}`.

```python
result = create_task(
    schedule="server-maintenance",
    name="nightly-backup",
    command="/opt/backup.sh",
    description="Nightly backup script",
    interval="0 2 * * *",
    stdout_handling="report",
    stderr_handling="merge",
)
```

Full signature:

```python
create_task(
    schedule,                   # Schedule name (required)
    name,                       # Task name (required)
    command,                    # Command to execute (required)
    description="",             # Comment text
    interval="",                # Cron expression
    run_at=None,                # ISO datetime string for one-off tasks
    starts_at=None,             # ISO datetime string
    ends_at=None,               # ISO datetime string
    stdout_handling="inherit",  # inherit | report | null | file
    stderr_handling="inherit",  # inherit | report | null | merge | file
    log_file="",                # Log file path
    server_url=None,            # Override .task.env
    api_token=None,             # Override .task.env
    ca_cert=None,               # Override .task.env
)
```
