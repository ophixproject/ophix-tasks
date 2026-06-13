"""
ophix-manage import_tasks
~~~~~~~~~~~~~~~~~~~~~~~~~
Import Schedule and ScheduledTask records from a JSON file produced by
export_tasks.

Idempotent: schedules are matched by name. Existing schedules are updated only
when a field value differs; identical records are skipped. Tasks within a
schedule are matched by name — existing tasks are updated when changed, new
tasks are created. Tasks present on the target but absent from the import file
are left untouched (no deletions).

If the file includes client_links and --include-client-links is passed, the
ClientScheduleAccess join records are also imported. Referenced clients and
hosts must already exist — run import_hosts and import_clients first.

Scheduler types (cron, systemd, etc.) are installed by data migrations and
must be present on the target server. Run migrate if a scheduler is reported
as missing.

Examples
--------
Import schedules and tasks:
    ophix-manage import_tasks --input-file tasks.json

Import with client links:
    ophix-manage import_tasks --input-file tasks.json --include-client-links

Preview without writing:
    ophix-manage import_tasks --input-file tasks.json --dry-run
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_datetime


class Command(BaseCommand):
    help = "Import Schedule and ScheduledTask records from a JSON file produced by export_tasks."

    def add_arguments(self, parser):
        parser.add_argument(
            "--input-file",
            required=True,
            metavar="FILE",
            help="Source file path (JSON produced by export_tasks).",
        )
        parser.add_argument(
            "--include-client-links",
            action="store_true",
            help="Also import ClientScheduleAccess join records from the file (if present).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created or updated without making any changes.",
        )
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="Suppress per-record output. Summary line is always shown.",
        )
        parser.add_argument(
            "--name",
            metavar="NAME",
            action="append",
            dest="names",
            default=None,
            help="Only import schedule(s) with this name. Repeat to specify multiple names.",
        )

    def handle(self, *args, **options):
        from ophix_tasks.models import Schedule, ScheduledTask, ClientScheduleAccess, Scheduler

        input_path   = Path(options["input_file"])
        import_links = options["include_client_links"]
        dry_run      = options["dry_run"]
        quiet        = options["quiet"]
        names        = options["names"]

        if not input_path.exists():
            raise CommandError(f"Input file not found: {input_path}")

        try:
            payload = json.loads(input_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CommandError(f"Invalid JSON in {input_path}: {exc}")

        if not isinstance(payload, dict) or "schedules" not in payload:
            raise CommandError("Unrecognised file format — expected export_tasks output.")

        records = payload["schedules"]
        if not isinstance(records, list):
            raise CommandError("Expected 'schedules' to be a JSON array.")

        if names:
            names_set = set(names)
            records = [r for r in records if (r.get("name") or "").strip() in names_set]
            if not records:
                raise CommandError(
                    f"No records found matching --name filter: {', '.join(sorted(names_set))}"
                )

        # Pre-load all known schedulers to avoid per-record DB hits.
        schedulers = {s.name: s for s in Scheduler.objects.all()}

        schedules_created = schedules_updated = schedules_unchanged = schedules_skipped = 0
        tasks_created = tasks_updated = tasks_unchanged = tasks_skipped = 0
        links_created = links_updated = links_unchanged = links_skipped = 0

        for i, rec in enumerate(records, 1):
            name = (rec.get("name") or "").strip()
            if not name:
                self.stderr.write(f"  Record {i}: missing 'name' — skipped.")
                schedules_skipped += 1
                continue

            schedule_fields = {
                "description": rec.get("description") or "",
                "enabled":     bool(rec.get("enabled", True)),
                "paused":      bool(rec.get("paused", False)),
            }

            # Create or update schedule.
            schedule_obj = None
            try:
                schedule_obj = Schedule.objects.get(name=name)
                changed = {
                    f: v for f, v in schedule_fields.items()
                    if getattr(schedule_obj, f) != v
                }
                if not changed:
                    schedules_unchanged += 1
                    if not quiet:
                        self.stdout.write(f"  {name}: unchanged.")
                else:
                    if not quiet:
                        self.stdout.write(f"  {name}: updating {', '.join(changed)}.")
                    if not dry_run:
                        try:
                            for f, v in changed.items():
                                setattr(schedule_obj, f, v)
                            schedule_obj.full_clean()
                            schedule_obj.save()
                        except Exception as exc:
                            self.stderr.write(f"  {name}: save failed — {exc}")
                            schedules_skipped += 1
                            continue
                    schedules_updated += 1

            except Schedule.DoesNotExist:
                if not quiet:
                    self.stdout.write(f"  {name}: creating.")
                if not dry_run:
                    try:
                        schedule_obj = Schedule(name=name, **schedule_fields)
                        schedule_obj.full_clean()
                        schedule_obj.save()
                    except Exception as exc:
                        self.stderr.write(f"  {name}: save failed — {exc}")
                        schedules_skipped += 1
                        continue
                schedules_created += 1

            # Import tasks nested under this schedule.
            for task_rec in (rec.get("tasks") or []):
                task_name = (task_rec.get("name") or "").strip()
                if not task_name:
                    self.stderr.write(f"  {name} / (unnamed task): missing 'name' — skipped.")
                    tasks_skipped += 1
                    continue

                # Resolve optional scheduler reference.
                scheduler_name = task_rec.get("scheduler")
                scheduler_obj = None
                if scheduler_name:
                    scheduler_obj = schedulers.get(scheduler_name)
                    if scheduler_obj is None:
                        self.stderr.write(
                            f"  {name} / {task_name}: scheduler '{scheduler_name}' not found — skipped. "
                            "Run migrate to ensure all schedulers are installed."
                        )
                        tasks_skipped += 1
                        continue

                task_fields = {
                    "command":         task_rec.get("command", ""),
                    "description":     task_rec.get("description") or "",
                    "scheduler":       scheduler_obj,
                    "interval":        task_rec.get("interval") or "",
                    "run_at":          parse_datetime(task_rec["run_at"]) if task_rec.get("run_at") else None,
                    "starts_at":       parse_datetime(task_rec["starts_at"]) if task_rec.get("starts_at") else None,
                    "ends_at":         parse_datetime(task_rec["ends_at"]) if task_rec.get("ends_at") else None,
                    "enabled":         bool(task_rec.get("enabled", True)),
                    "paused":          bool(task_rec.get("paused", False)),
                    "stdout_handling": task_rec.get("stdout_handling", "inherit"),
                    "stderr_handling": task_rec.get("stderr_handling", "inherit"),
                    "log_file":        task_rec.get("log_file") or "",
                }

                if dry_run or schedule_obj is None:
                    tasks_created += 1
                    continue

                try:
                    task_obj = ScheduledTask.objects.get(schedule=schedule_obj, name=task_name)
                    changed = {}
                    for f, v in task_fields.items():
                        current = getattr(task_obj, f)
                        # FK comparison: compare pk
                        if hasattr(v, "pk"):
                            if getattr(current, "pk", None) != v.pk:
                                changed[f] = v
                        elif str(current) != str(v):
                            changed[f] = v
                    if not changed:
                        tasks_unchanged += 1
                    else:
                        if not quiet:
                            self.stdout.write(
                                f"  {name} / {task_name}: updating {', '.join(changed)}."
                            )
                        try:
                            for f, v in changed.items():
                                setattr(task_obj, f, v)
                            task_obj.full_clean()
                            task_obj.save()
                        except Exception as exc:
                            self.stderr.write(
                                f"  {name} / {task_name}: save failed — {exc}"
                            )
                            tasks_skipped += 1
                            continue
                        tasks_updated += 1

                except ScheduledTask.DoesNotExist:
                    if not quiet:
                        self.stdout.write(f"  {name} / {task_name}: creating.")
                    try:
                        task_obj = ScheduledTask(schedule=schedule_obj, name=task_name, **task_fields)
                        task_obj.full_clean()
                        task_obj.save()
                    except Exception as exc:
                        self.stderr.write(f"  {name} / {task_name}: save failed — {exc}")
                        tasks_skipped += 1
                        continue
                    tasks_created += 1

            # Import client links if requested.
            if import_links and rec.get("client_links"):
                if dry_run or schedule_obj is None:
                    links_created += len(rec["client_links"])
                    continue

                from ophix.core.models import Client, Host
                for link_rec in rec["client_links"]:
                    client_name = (link_rec.get("client") or "").strip()
                    host_name   = (link_rec.get("host") or "").strip()

                    if not client_name or not host_name:
                        self.stderr.write(
                            f"  {name} → link: missing client or host — skipped."
                        )
                        links_skipped += 1
                        continue

                    try:
                        host   = Host.objects.get(name=host_name)
                        client = Client.objects.get(name=client_name, host=host)
                    except Host.DoesNotExist:
                        self.stderr.write(
                            f"  {name} → {host_name}/{client_name}: "
                            f"host '{host_name}' not found — skipped."
                        )
                        links_skipped += 1
                        continue
                    except Client.DoesNotExist:
                        self.stderr.write(
                            f"  {name} → {host_name}/{client_name}: "
                            f"client not found — skipped."
                        )
                        links_skipped += 1
                        continue

                    link_fields = {
                        "enabled":    bool(link_rec.get("enabled", True)),
                        "can_update": bool(link_rec.get("can_update", False)),
                        "can_delete": bool(link_rec.get("can_delete", False)),
                        "can_share":  bool(link_rec.get("can_share", False)),
                        "paused":     bool(link_rec.get("paused", False)),
                        "notes":      link_rec.get("notes") or None,
                    }

                    try:
                        link = ClientScheduleAccess.objects.get(
                            client=client, schedule=schedule_obj
                        )
                        link_changed = {
                            f: v for f, v in link_fields.items()
                            if getattr(link, f) != v
                        }
                        if not link_changed:
                            links_unchanged += 1
                        else:
                            if not quiet:
                                self.stdout.write(
                                    f"  {name} → {host_name}/{client_name}: "
                                    f"updating {', '.join(link_changed)}."
                                )
                            try:
                                for f, v in link_changed.items():
                                    setattr(link, f, v)
                                link.save()
                            except Exception as exc:
                                self.stderr.write(
                                    f"  {name} → {host_name}/{client_name}: "
                                    f"save failed — {exc}"
                                )
                                links_skipped += 1
                                continue
                            links_updated += 1

                    except ClientScheduleAccess.DoesNotExist:
                        if not quiet:
                            self.stdout.write(
                                f"  {name} → {host_name}/{client_name}: creating link."
                            )
                        try:
                            ClientScheduleAccess.objects.create(
                                client=client, schedule=schedule_obj, **link_fields
                            )
                        except Exception as exc:
                            self.stderr.write(
                                f"  {name} → {host_name}/{client_name}: "
                                f"save failed — {exc}"
                            )
                            links_skipped += 1
                            continue
                        links_created += 1

        # Build summary.
        sched_parts = []
        if schedules_created:
            sched_parts.append(f"{schedules_created} created")
        if schedules_updated:
            sched_parts.append(f"{schedules_updated} updated")
        if schedules_unchanged:
            sched_parts.append(f"{schedules_unchanged} unchanged")
        if schedules_skipped:
            sched_parts.append(f"{schedules_skipped} skipped")
        sched_summary = ", ".join(sched_parts) if sched_parts else "nothing to do"

        task_parts = []
        if tasks_created:
            task_parts.append(f"{tasks_created} created")
        if tasks_updated:
            task_parts.append(f"{tasks_updated} updated")
        if tasks_unchanged:
            task_parts.append(f"{tasks_unchanged} unchanged")
        if tasks_skipped:
            task_parts.append(f"{tasks_skipped} skipped")
        task_summary = ", ".join(task_parts) if task_parts else "none"

        summary = f"Schedules: {sched_summary} | Tasks: {task_summary}"

        if import_links:
            link_parts = []
            if links_created:
                link_parts.append(f"{links_created} created")
            if links_updated:
                link_parts.append(f"{links_updated} updated")
            if links_unchanged:
                link_parts.append(f"{links_unchanged} unchanged")
            if links_skipped:
                link_parts.append(f"{links_skipped} skipped")
            link_summary = ", ".join(link_parts) if link_parts else "none"
            summary += f" | Links: {link_summary}"

        if dry_run:
            self.stdout.write(f"Dry run: {summary}.")
        else:
            self.stdout.write(self.style.SUCCESS(f"{summary}."))
