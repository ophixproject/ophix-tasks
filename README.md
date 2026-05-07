# ophix-tasks

Task scheduling domain plugin for [Ophix Project](https://ophixproject.com) servers.

Provides a central schedule store for fleet hosts. Operators define named Schedules containing individual tasks. Clients are granted access to one or more Schedules and receive all active tasks in a single API call. Tier 2 clients apply the task list to the host's native scheduler.

---

## Installation

```bash
pip install ophix-tasks
```

Install alongside `ophix-server-base` and any other plugins for your server instance.

---

## Concepts

### Schedule

A named collection of tasks. This is the artifact — clients are linked at the Schedule level and receive all active tasks within it. A host might be linked to `server-maintenance` and `application-tasks` and receive all tasks from both.

### ScheduledTask

An individual task within a Schedule. Defines what to run and when.

Each task has exactly one scheduling mode:

| Field | Purpose |
| --- | --- |
| `run_at` | One-off: exact datetime to execute |
| `interval` | Recurring: standard cron expression (e.g. `0 2 * * *`) |

Time bounds are optional and enforced server-side — the server omits tasks outside their active window from API responses:

| Field | Meaning |
| --- | --- |
| `starts_at` | Do not include in responses before this datetime |
| `ends_at` | Stop including in responses after this datetime |

Both set → bounded window. Only `starts_at` → delayed start. Only `ends_at` → run until this date.

> **Note:** Schedule precision is bounded by the client's sync interval. If a task starts at 09:00 and the client syncs hourly, it may not be picked up until 10:00. Tune the sync interval to the precision you need.

### ClientScheduleAccess

Links a Client to a Schedule with the standard Ophix permission flags (`enabled`, `can_update`, `can_delete`, `can_share`). Disabling the access record, the Schedule, the Client, or its Host all block task delivery.

---

## API

### `GET /api/tasks/`

Returns a flat JSON array of all currently active tasks for the authenticated client, aggregated across all linked Schedules. Only tasks within their `starts_at`/`ends_at` window (if set) are included.

```json
[
  {
    "id": 1,
    "schedule": "server-maintenance",
    "name": "nightly-backup",
    "command": "/opt/myapp/backup.sh",
    "run_at": null,
    "interval": "0 2 * * *",
    "starts_at": null,
    "ends_at": null
  },
  {
    "id": 2,
    "schedule": "server-maintenance",
    "name": "one-time-cleanup",
    "command": "/opt/myapp/cleanup.sh",
    "run_at": "2026-06-01T09:30:00Z",
    "interval": null,
    "starts_at": null,
    "ends_at": "2026-06-01T23:59:59Z"
  }
]
```

Authentication requires a valid token and matching source IP (standard Ophix client auth).

---

## Admin

Two admin views are provided:

**Schedules** — primary management view. Shows all Schedules with task count and linked clients. Tasks are edited inline. Client access is managed inline.

**Scheduled Tasks** — granular task-level view. Filter by schedule, enable/disable individual tasks, edit timing fields directly. Use this when you need to work across many tasks without opening each Schedule.

---

## Settings

| Setting | Default | Description |
| --- | --- | --- |
| `SERVER_NAME` | `taskserver` | Human-readable name shown in the admin footer |

Set in `.env`. All other behaviour is controlled via the admin UI.

---

## Server setup

```bash
pip install ophix-tasks ophix-server-base ophix-docs
ophix-manage configure_install taskserver
ophix-manage run_install taskserver
sudo bash taskserver_sudo_install.sh
```

After installation, create Schedules and tasks in the admin UI, then link clients to Schedules to grant access.
