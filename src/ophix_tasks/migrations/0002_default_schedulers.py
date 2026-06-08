"""
Data migration: seed the built-in Scheduler rows.

cron    — /etc/cron.d, 5-field cron expressions
systemd — systemd timer units, OnCalendar= expressions
wts     — Windows Task Scheduler (disabled by default; requires ophix-task-wts)
"""

from django.db import migrations


SCHEDULERS = [
    {
        "name": "cron",
        "label": "Cron (/etc/cron.d)",
        "interval_help": (
            "5-field cron expression: minute hour day-of-month month day-of-week\n"
            "Examples: 0 2 * * * (daily at 2am), */15 * * * * (every 15 minutes)\n"
            "Shorthands: @daily @weekly @monthly @hourly @reboot"
        ),
        "validator_class": "ophix_tasks.validators.CronValidator",
        "enabled": True,
    },
    {
        "name": "systemd",
        "label": "systemd Timer Units",
        "interval_help": (
            "systemd OnCalendar= expression\n"
            "Examples: *-*-* 02:00:00 (daily at 2am), daily, Mon *-*-* 08:00:00\n"
            "Reference: man systemd.time(7)"
        ),
        "validator_class": "ophix_tasks.validators.SystemdValidator",
        "enabled": True,
    },
    {
        "name": "wts",
        "label": "Windows Task Scheduler",
        "interval_help": (
            "WTS trigger: DAILY HH:MM | WEEKLY DOW HH:MM | MONTHLY DOM HH:MM | ONCE YYYY-MM-DD HH:MM\n"
            "Examples: DAILY 02:00, WEEKLY Mon 08:00, MONTHLY 1 09:00\n"
            "Requires: ophix-task-wts Tier 2 client"
        ),
        "validator_class": "ophix_tasks.validators.WtsValidator",
        "enabled": False,
    },
]


def create_schedulers(apps, schema_editor):
    Scheduler = apps.get_model("ophix_tasks", "Scheduler")
    for data in SCHEDULERS:
        Scheduler.objects.get_or_create(name=data["name"], defaults=data)


def remove_schedulers(apps, schema_editor):
    Scheduler = apps.get_model("ophix_tasks", "Scheduler")
    Scheduler.objects.filter(name__in=[s["name"] for s in SCHEDULERS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("ophix_tasks", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_schedulers, reverse_code=remove_schedulers),
    ]
