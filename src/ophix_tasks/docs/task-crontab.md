---
title: task-crontab Reference
slug: task-crontab
order: 120
section: Task Scheduling
---

# task-crontab Reference

`ophix-task-crontab` is the Tier 2 cron client for the task scheduling domain. It fetches the task list from the task server via `task_client.core` and writes a managed block to a `/etc/cron.d/` file using sentinel comments. The entire block is reconstructed on every sync.

---

## Installation

```bash
pip install ophix-task-crontab
```

`ophix-task-client` is a required dependency and is installed automatically.

---

## How It Works

### Managed Block

task-crontab writes a single contiguous block delimited by sentinel comments:

```
# --- BEGIN OPHIX-TASKS (managed by ophix-task-crontab, do not edit) ---
# Nightly backup script
0 2 * * * root /opt/backup.sh | task-client report 1  # nightly-backup
# [disabled] 30 9 * * * root /opt/cleanup.sh  # disabled-cleanup
# --- END OPHIX-TASKS ---
```

On each sync, the existing block is replaced atomically. Content outside the sentinels is preserved — you can have other entries in the same file.

### cron.d Format

Files in `/etc/cron.d/` require a username field between the schedule and the command. task-crontab uses this format by default (defaulting to `root`). Override with `--user`.

### Disabled Tasks

Tasks with `enabled=False` are written as commented-out lines prefixed with `# [disabled]`. This makes it visible that a task has been suspended rather than silently removing it.

### Output Handling

The cron line is built from the task's `stdout_handling` and `stderr_handling` fields:

| stdout | stderr | Generated command |
| --- | --- | --- |
| `inherit` | `inherit` | `command` |
| `report` | `inherit` | `command \| task-client report <id>` |
| `report` | `report` or `merge` | `command 2>&1 \| task-client report <id>` |
| `report` | `null` | `command 2>/dev/null \| task-client report <id>` |
| `inherit` | `report` | `command 2>&1 1>/dev/null \| task-client report <id>` |
| `null` | `inherit` | `command > /dev/null` |
| `file` | `merge` | `command >> /path/to/log 2>&1` |
| `null` | `null` | `command > /dev/null 2>/dev/null` |

`task-client report` reads from stdin and POSTs to the server. Failures are silently ignored.

### One-Off Tasks

Tasks with `run_at` set are converted to a pinned cron expression: `MM HH DD month *`. The server stops returning the task after `ends_at` has passed, so the entry is removed on the next sync before it can fire again in a future year.

---

## Commands

### `sync`

Fetch tasks and write to the crontab file.

```bash
task-crontab sync
task-crontab sync --schedule server-maintenance
task-crontab sync --user www-data --file /etc/cron.d/ophix-www
```

| Argument | Default | Description |
| --- | --- | --- |
| `--schedule` | (all) | Only fetch tasks from this named Schedule |
| `--file` | `/etc/cron.d/ophix-tasks` | Crontab file to write |
| `--user` | `root` | Unix user to run tasks as |

Requires write permission to the target file. Run as root or via sudo.

### `show`

Print the cron block that would be written, without writing anything. Useful for review before applying.

```bash
task-crontab show
task-crontab show --schedule server-maintenance --user www-data
```

| Argument | Default | Description |
| --- | --- | --- |
| `--schedule` | (all) | Only fetch tasks from this named Schedule |
| `--user` | `root` | Unix user to run tasks as |

### `clear`

Remove the ophix-managed block from the crontab file.

```bash
task-crontab clear
task-crontab clear --file /etc/cron.d/ophix-www
```

| Argument | Default | Description |
| --- | --- | --- |
| `--file` | `/etc/cron.d/ophix-tasks` | Crontab file to modify |

### `import`

Parse an existing crontab and create tasks on the server. Useful for bootstrapping — move existing cron jobs into Ophix without re-entering them manually.

```bash
# Import the current user's crontab (crontab -l)
task-crontab import --schedule server-maintenance

# Import from a specific file (e.g. an existing cron.d file)
task-crontab import --schedule server-maintenance --file /etc/cron.d/myapp
```

| Argument | Required | Description |
| --- | --- | --- |
| `--schedule` | Yes | Schedule name to import tasks into |
| `--file` | No | File to read (default: reads from `crontab -l`) |

The client must have `can_update` access to the Schedule.

**Import behaviour:**

- Comment lines immediately preceding a cron entry are captured as the task `description`
- The existing cron expression (or `@special` shorthand) is used as the `interval`
- The `name` is derived from the command basename
- If a task with the same command already exists in the Schedule, it is skipped
- The existing ophix-managed sentinel block is skipped automatically
- Environment variable assignments (`MAILTO=""`, etc.) are skipped

After import, run `task-crontab sync` to apply the tasks back from the server.

---

## Multi-Schedule and Multi-User Setup

A single host can manage multiple cron.d files, each populated from a different Schedule:

```bash
# Root jobs — e.g. system maintenance
task-crontab sync --schedule server-maintenance --file /etc/cron.d/ophix-root --user root

# Web server jobs — run as www-data
task-crontab sync --schedule www-data-tasks --file /etc/cron.d/ophix-www --user www-data

# Database jobs — run as postgres
task-crontab sync --schedule postgres-tasks --file /etc/cron.d/ophix-postgres --user postgres
```

Typically each sync call is itself a scheduled task — define it in the appropriate Schedule and include it in the cron.d file. Use a fixed interval, not a task-crontab-managed entry, to bootstrap the first sync.

The server allows a single client to hold access to multiple Schedules simultaneously. There is no enforced limit. Operators are responsible for ensuring that two sync calls do not write different content to the same file (one will overwrite the other).

---

## Scheduling the Sync

To keep the crontab in sync automatically, add the sync call as a root cron entry outside the managed block:

```
# /etc/cron.d/ophix-tasks
*/15 * * * * root /opt/venv/bin/task-crontab sync --schedule server-maintenance
```

Or add it as a task in a separate self-referencing Schedule (use a fixed file entry for bootstrapping).
