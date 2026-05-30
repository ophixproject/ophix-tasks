"""
ophix-manage export_tasks
~~~~~~~~~~~~~~~~~~~~~~~~~
Export Schedule records (and their ScheduledTask children) to a JSON file for
backup or server migration.

Execution logs are not exported — they are operational data, not configuration.

Use --include-client-links to also export ClientScheduleAccess join records
(which clients have access to which schedules and with what permissions).
On import, referenced clients and hosts must already exist — run import_hosts
and import_clients first when doing a full server restore.

Examples
--------
Export all schedules and tasks:
    ophix-manage export_tasks --output-file tasks.json

Export with client links included:
    ophix-manage export_tasks --output-file tasks.json --include-client-links

Preview without writing:
    ophix-manage export_tasks --output-file tasks.json --dry-run
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError


def _serialize_task(task):
    return {
        "name":            task.name,
        "command":         task.command,
        "description":     task.description,
        "scheduler":       task.scheduler.name if task.scheduler else None,
        "interval":        task.interval,
        "run_at":          task.run_at.isoformat() if task.run_at else None,
        "starts_at":       task.starts_at.isoformat() if task.starts_at else None,
        "ends_at":         task.ends_at.isoformat() if task.ends_at else None,
        "enabled":         task.enabled,
        "paused":          task.paused,
        "stdout_handling": task.stdout_handling,
        "stderr_handling": task.stderr_handling,
        "log_file":        task.log_file,
    }


def _serialize_schedule(schedule, include_links=False):
    record = {
        "name":        schedule.name,
        "description": schedule.description,
        "enabled":     schedule.enabled,
        "paused":      schedule.paused,
        "tasks":       [
            _serialize_task(t)
            for t in schedule.tasks.select_related("scheduler").order_by("name")
        ],
    }

    if include_links:
        links = []
        for link in schedule.client_access.select_related("client__host").all():
            links.append({
                "client":     link.client.name,
                "host":       link.client.host.name,
                "enabled":    link.enabled,
                "can_update": link.can_update,
                "can_delete": link.can_delete,
                "can_share":  link.can_share,
                "paused":     link.paused,
                "notes":      link.notes,
            })
        record["client_links"] = links

    return record


class Command(BaseCommand):
    help = "Export Schedule and ScheduledTask records to a JSON file for backup or server migration."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-file",
            required=True,
            metavar="FILE",
            help="Destination file path.",
        )
        parser.add_argument(
            "--include-client-links",
            action="store_true",
            help="Also export ClientScheduleAccess join records (client access and permission flags).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show how many schedules would be exported without writing anything.",
        )
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="Suppress all output.",
        )

    def handle(self, *args, **options):
        from ophix_tasks.models import Schedule

        output_path   = Path(options["output_file"])
        include_links = options["include_client_links"]
        dry_run       = options["dry_run"]
        quiet         = options["quiet"]

        schedules = list(Schedule.objects.order_by("name"))
        count     = len(schedules)
        task_count = sum(s.tasks.count() for s in schedules)

        if dry_run:
            self.stdout.write(
                f"Dry run: {count} schedule(s) with {task_count} task(s) "
                f"would be exported to {output_path}."
            )
            return

        if count == 0:
            if not quiet:
                self.stdout.write("No schedules found — nothing to export.")
            return

        if not output_path.parent.exists():
            raise CommandError(f"Output directory does not exist: {output_path.parent}")

        payload = {
            "version":              1,
            "include_client_links": include_links,
            "schedules":            [
                _serialize_schedule(s, include_links) for s in schedules
            ],
        }

        with output_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        if not quiet:
            link_note = ", with client links" if include_links else ""
            self.stdout.write(self.style.SUCCESS(
                f"Exported {count} schedule(s) with {task_count} task(s) "
                f"to {output_path}{link_note}."
            ))
