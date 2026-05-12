---
title: task-crontab Reference
slug: task-crontab
order: 120
section: Task Scheduling
---

`ophix-task-crontab` is the Tier 2 cron client for the task scheduling domain. It fetches the task list from the task server via `task_client.core` and writes a managed block to a `/etc/cron.d/` file using sentinel comments. The entire block is reconstructed on every sync.

---

## Installation

```bash
pip install ophix-task-crontab
```

`ophix-task-client` is a required dependency and is installed automatically.

---

## How It Works

### Output Format

task-crontab supports two output formats:

| Format | When used | Username field |
| --- | --- | --- |
| `crond` | Default when running as root | Yes — `schedule username command` |
| `user` | Default when running as non-root | No — `schedule command` |

Override with `--format user` or `--format crond`. In `user` format, `--user` is ignored.

### Managed Block

task-crontab writes a single contiguous block delimited by sentinel comments:

```text
# --- BEGIN OPHIX-TASKS (managed by ophix-task-crontab, do not edit) ---

# Nightly backup script
0 2 * * * root /opt/backup.sh | task-client report 1

# [paused] 30 9 * * * root /opt/report.sh
# --- END OPHIX-TASKS ---
```

On each sync, the existing block is replaced atomically. Content outside the sentinels is preserved — you can have other entries in the same file.

### cron.d Format

Files in `/etc/cron.d/` require a username field between the schedule and the command. task-crontab uses this format when running as root (defaulting to `root`). Override with `--user`.

### Disabled and Paused Tasks

- **`enabled=False`** — the task is not returned by the server. On the next sync, the entry is removed from the crontab entirely. This matches the behaviour of all other Ophix domains.
- **`paused=True`** — the task is returned by the server but written as a commented-out line with `# [paused]`. The entry is visible so the operator can see that a task has been temporarily suspended.

Task descriptions are written as comment lines immediately above the cron entry. No name suffix is appended to any line.

### Output Handling

The cron line is built from the task's `stdout_handling` and `stderr_handling` fields:

| stdout | stderr | Generated command | Stream logged |
| --- | --- | --- | --- |
| `inherit` | `inherit` | `command` | — |
| `report` | `inherit` | `command \| task-client report <id> --stream stdout` | stdout |
| `report` | `report` or `merge` | `command 2>&1 \| task-client report <id> --stream both` | both |
| `report` | `null` | `command 2>/dev/null \| task-client report <id> --stream stdout` | stdout |
| `null` | `report` | `command > /dev/null 2>&1 1>/dev/null \| task-client report <id> --stream stderr` | stderr |
| `null` | `inherit` | `command > /dev/null` | — |
| `file` | `merge` | `command >> /path/to/log 2>&1` | — |
| `null` | `null` | `command > /dev/null 2>/dev/null` | — |

`task-client report` reads from stdin and POSTs to the server. If stdin is empty, no log entry is created — the report is silently skipped. Pass `--force` to record an entry even when there is no output. Failures are silently ignored.

While `task-client report` is designed to be called from a generated cron line, it is a general-purpose command with no requirement to be used that way. You can call it from any context — a script, a wrapper, or the command line — and pipe any input to it:

```bash
echo "Manual note: deployed v2.3 at 14:30" | task-client report 42
some-script.sh 2>&1 | task-client report 42 --stream both
```

#### The pipe constraint

`task-client report` receives output via a shell pipe, which carries a single stream. This means:

- When both stdout and stderr go to the reporter, they **must be merged** (`2>&1`) before the pipe — there is no way to deliver them separately through one pipe. Both `stderr=report` and `stderr=merge` produce the same shell construct; the difference is only labelling intent.
- When stdout and stderr go to **different destinations** (e.g. stdout to a file, stderr to the reporter), each gets its own independent redirect and they remain separate.

#### Non-standard output handling

If the built-in options don't cover your needs, set both fields to `inherit` and write the redirections directly in the command field:

```text
/opt/myscript.sh 2>/var/log/myscript-errors.log | tee /var/log/myscript.log | task-client report 42 --stream stdout
```

task-crontab writes the command field verbatim, so any shell construct is valid.

### One-Off Tasks

Tasks with `run_at` set are converted to a pinned cron expression: `MM HH DD month *`. The server stops returning the task after `ends_at` has passed, so the entry is removed on the next sync before it can fire again in a future year.

---

## Commands

### `sync`

Fetch tasks and write to the crontab.

```bash
# As a non-root user — writes to your user crontab automatically
task-crontab sync --schedule my-schedule

# As root — writes to /etc/cron.d/ophix-tasks (crond format)
task-crontab sync --schedule server-maintenance

# Override format or file explicitly
task-crontab sync --format crond --user www-data --file /etc/cron.d/ophix-www
```

| Argument | Default | Description |
| --- | --- | --- |
| `--schedule` | (all) | Only fetch tasks from this named Schedule |
| `--file` | auto | File to write. When non-root and not specified, writes via `crontab -` |
| `--user` | `root` | Unix user to run tasks as (crond format only) |
| `--format` | auto | `user` (no username field) or `crond` (username field). Default: auto-detect from UID |

When running as root without `--file`, writes to `/etc/cron.d/ophix-tasks`. When running as non-root without `--file`, reads the user crontab with `crontab -l` and writes it back via `crontab -`.

### `show`

Print the cron block that would be written, without writing anything. Useful for review before applying.

```bash
task-crontab show
task-crontab show --schedule server-maintenance --user www-data
task-crontab show --format user
```

| Argument | Default | Description |
| --- | --- | --- |
| `--schedule` | (all) | Only fetch tasks from this named Schedule |
| `--user` | `root` | Unix user to run tasks as (crond format only) |
| `--format` | auto | `user` or `crond`. Default: auto-detect from UID |

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
- Shell output redirections (`> /dev/null 2>&1`, `>> /path/to/file`, etc.) are detected and stripped from the command, with the equivalent `stdout_handling` / `stderr_handling` fields set automatically
- If a task with the same command and interval already exists in the Schedule, it is skipped
- The existing ophix-managed sentinel block is skipped automatically
- Environment variable assignments (`MAILTO=""`, etc.) are skipped

After import, run `task-crontab sync` to apply the tasks back from the server.

#### Use full paths for commands

It is good practice to use absolute paths for all executables in cron entries (`/usr/bin/date` rather than `date`). There are two reasons:

1. **Runtime reliability** — cron runs with a minimal `PATH` that often excludes directories on your interactive shell's path. A command that works at the terminal may fail silently under cron if it is not referenced by its full path.
2. **Import parsing** — the importer auto-detects cron.d format (which has a username field between the schedule and the command) by checking whether the first word after the schedule looks like a username. A bare command name such as `date` or `curl` that contains no `/` can be misidentified as a username, resulting in a blank command and a server error. Using a full path (`/usr/bin/date`) avoids this ambiguity entirely.

If you encounter a `command may not be blank` error during import, check whether the first token of the command is a bare word — replacing it with its full path will resolve it.

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

```text
# /etc/cron.d/ophix-tasks
*/15 * * * * root /opt/venv/bin/task-crontab sync --schedule server-maintenance
```

Or add it as a task in a separate self-referencing Schedule (use a fixed file entry for bootstrapping).
