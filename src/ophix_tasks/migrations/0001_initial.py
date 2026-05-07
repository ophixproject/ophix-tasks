from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("ophix_core", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Schedule",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=100, unique=True, verbose_name="name")),
                ("description", models.TextField(blank=True, default="", verbose_name="description")),
                ("enabled", models.BooleanField(default=True, verbose_name="enabled")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="updated at")),
            ],
            options={
                "verbose_name": "Schedule",
                "verbose_name_plural": "Schedules",
                "ordering": ("name",),
            },
        ),
        migrations.CreateModel(
            name="ScheduledTask",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                (
                    "schedule",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tasks",
                        to="ophix_tasks.schedule",
                        verbose_name="schedule",
                    ),
                ),
                ("name", models.CharField(max_length=200, verbose_name="name")),
                ("command", models.TextField(verbose_name="command")),
                ("run_at", models.DateTimeField(blank=True, null=True, verbose_name="run at")),
                ("interval", models.CharField(blank=True, default="", max_length=100, verbose_name="interval")),
                ("starts_at", models.DateTimeField(blank=True, null=True, verbose_name="starts at")),
                ("ends_at", models.DateTimeField(blank=True, null=True, verbose_name="ends at")),
                ("enabled", models.BooleanField(default=True, verbose_name="enabled")),
                ("report_output", models.BooleanField(default=False, verbose_name="report output")),
                ("report_error", models.BooleanField(default=False, verbose_name="report errors")),
            ],
            options={
                "verbose_name": "Scheduled Task",
                "verbose_name_plural": "Scheduled Tasks",
                "ordering": ("schedule__name", "name"),
            },
        ),
        migrations.CreateModel(
            name="ClientScheduleAccess",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                (
                    "client",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="ophix_core.client",
                        verbose_name="client",
                    ),
                ),
                ("enabled", models.BooleanField(default=True, verbose_name="enabled")),
                ("can_update", models.BooleanField(default=False, verbose_name="can update")),
                ("can_delete", models.BooleanField(default=False, verbose_name="can delete")),
                ("can_share", models.BooleanField(default=False, verbose_name="can share")),
                ("notes", models.TextField(blank=True, default="", verbose_name="notes")),
                (
                    "schedule",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="client_access",
                        to="ophix_tasks.schedule",
                        verbose_name="schedule",
                    ),
                ),
            ],
            options={
                "verbose_name": "Client Schedule Access",
                "verbose_name_plural": "Client Schedule Access",
                "unique_together": {("client", "schedule")},
            },
        ),
    ]
