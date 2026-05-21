"""
ophix-manage prune_task_logs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Delete TaskExecutionLog records older than N days.

Intended to be run periodically via cron to keep the execution log table
from growing unbounded. Operates in a single DELETE query.

Examples
--------
Delete records older than 90 days (default):
    ophix-manage prune_task_logs

Delete records older than 30 days:
    ophix-manage prune_task_logs --days 30

Preview how many records would be removed without deleting:
    ophix-manage prune_task_logs --dry-run
    ophix-manage prune_task_logs --days 30 --dry-run
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Delete TaskExecutionLog records older than N days (default 90)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=None,
            metavar="N",
            help="Delete records older than this many days (default: PRUNE_TASK_LOG_DAYS setting, or 90).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show how many records would be deleted without deleting them.",
        )
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="Suppress all output. Useful when running from cron.",
        )

    def handle(self, *args, **options):
        from django.conf import settings
        from ophix_tasks.models import TaskExecutionLog

        days = options["days"]
        if days is None:
            days = getattr(settings, "PRUNE_TASK_LOG_DAYS", 90)
        dry_run = options["dry_run"]
        quiet   = options["quiet"]

        cutoff = timezone.now() - timedelta(days=days)
        qs = TaskExecutionLog.objects.filter(reported_at__lt=cutoff)
        count = qs.count()

        if dry_run:
            self.stdout.write(
                f"Dry run: {count} record(s) older than {days} days would be deleted "
                f"(cutoff: {cutoff:%Y-%m-%d %H:%M:%S} UTC)."
            )
            return

        if count == 0:
            if not quiet:
                self.stdout.write(f"No task execution log records older than {days} days found.")
            return

        qs.delete()
        if not quiet:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Deleted {count} task execution log record(s) older than {days} days."
                )
            )
