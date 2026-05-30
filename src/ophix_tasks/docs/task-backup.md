---
title: Task Schedule Backup and Migration
slug: task-backup
order: 110
section: Task Scheduling
---

Schedule and task records can be exported to a JSON file and imported on another server. This supports server migration, disaster recovery, and environment cloning.

Task execution logs are not exported — they are operational data. Only the schedule definitions and task configuration are included.

---

## Restore dependency order

Schedule imports reference clients by name. The full restore sequence for a task server is:

```
import_hosts  →  import_clients  →  import_tasks
```

Run `import_hosts` and `import_clients` (from `ophix-server-base`) before importing schedules with client links. See [Server Backup and Migration](server-backup) for the base-layer commands.

If you are only restoring schedule definitions (no client links), `import_tasks` can run independently.

---

## Exporting schedules

**Export all schedules and tasks:**

```bash
ophix-manage export_tasks --output-file tasks.json
```

**Also export client access links:**

```bash
ophix-manage export_tasks --output-file tasks.json --include-client-links
```

**Preview without writing:**

```bash
ophix-manage export_tasks --output-file tasks.json --dry-run
```

| Flag | Description |
| --- | --- |
| `--output-file FILE` | _(required)_ Destination path |
| `--include-client-links` | Also export `ClientScheduleAccess` join records (client access and permission flags) |
| `--dry-run` | Show how many schedules and tasks would be exported without writing |
| `--quiet` | Suppress all output |

### What is exported

Each schedule record includes:

- `name` — the unique schedule identifier
- `description` — optional description text
- `enabled` / `paused` — schedule-level state flags
- `tasks` — all `ScheduledTask` records nested within the schedule

Each task record within `tasks` includes:

- `name`, `command`, `description`
- `scheduler` — the scheduler type name (e.g. `cron`, `systemd`)
- `interval` — the recurring interval expression, or blank for one-off tasks
- `run_at` — the one-off execution datetime (ISO 8601), or null for recurring tasks
- `starts_at` / `ends_at` — optional time bounds
- `enabled` / `paused` — task-level state flags
- `stdout_handling` / `stderr_handling` / `log_file` — output routing

With `--include-client-links`, each schedule record also includes its `ClientScheduleAccess` join records, capturing which clients have access and with what permission flags (`enabled`, `can_update`, `can_delete`, `can_share`, `paused`, `notes`).

---

## Importing schedules

**Import from a file:**

```bash
ophix-manage import_tasks --input-file tasks.json
```

**Also import client links:**

```bash
ophix-manage import_tasks --input-file tasks.json --include-client-links
```

**Preview without writing:**

```bash
ophix-manage import_tasks --input-file tasks.json --dry-run
```

Schedules are matched by name. Tasks within a schedule are matched by name within that schedule. Existing records are updated only when a field value differs; identical records are skipped. The import is idempotent — safe to re-run.

Tasks present on the target server but absent from the import file are left untouched. The import is additive: it creates and updates, but never deletes.

For client links, referenced hosts and clients must already exist on the target server. Missing hosts or clients are reported per-record and skipped; the schedule itself is still imported.

| Flag | Description |
| --- | --- |
| `--input-file FILE` | _(required)_ Source path (JSON produced by `export_tasks`) |
| `--include-client-links` | Also import `ClientScheduleAccess` join records from the file |
| `--dry-run` | Show what would be created or updated without making any changes |
| `--quiet` | Suppress per-record output; summary line always shown |

### Scheduler types

Scheduler types (`cron`, `systemd`, `wts`, etc.) are installed by data migrations. If a scheduler name referenced in a task is not present on the target server, that task is skipped with an error. Run `ophix-manage migrate` to ensure all scheduler types are installed before importing.

---

## Full task server restore workflow

```bash
# 1. Export from the source server
ophix-manage export_hosts --output-file hosts.json
ophix-manage export_clients --output-file clients.json --passphrase "client-passphrase"
ophix-manage export_tasks --output-file tasks.json --include-client-links

# 2. Transfer all three files to the target server

# 3. Import on the target server in dependency order
ophix-manage import_hosts --input-file hosts.json
ophix-manage import_clients --input-file clients.json --passphrase "client-passphrase"
ophix-manage import_tasks --input-file tasks.json --include-client-links
```

Fleet clients can reconnect and retrieve their schedules immediately after the restore without re-registering or re-linking.
