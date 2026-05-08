from django.db import migrations, models
import django.db.models.deletion


def populate_schedulers(apps, schema_editor):
    Scheduler = apps.get_model("ophix_tasks", "Scheduler")
    Scheduler.objects.bulk_create([
        Scheduler(
            name="cron",
            label="Cron (/etc/cron.d)",
            interval_help=(
                "5-field cron expression: minute hour day-of-month month day-of-week\n"
                "Examples: 0 2 * * * (daily at 2am), */15 * * * * (every 15 minutes)\n"
                "Shorthands: @daily @weekly @monthly @hourly @reboot"
            ),
            validator_class="ophix_tasks.validators.CronValidator",
            enabled=True,
        ),
        Scheduler(
            name="systemd",
            label="systemd Timer Units",
            interval_help=(
                "systemd OnCalendar= expression\n"
                "Examples: *-*-* 02:00:00 (daily at 2am), daily, Mon *-*-* 08:00:00\n"
                "Reference: man systemd.time(7)"
            ),
            validator_class="ophix_tasks.validators.SystemdValidator",
            enabled=True,
        ),
        Scheduler(
            name="wts",
            label="Windows Task Scheduler",
            interval_help=(
                "WTS trigger: DAILY HH:MM | WEEKLY DOW HH:MM | MONTHLY DOM HH:MM | ONCE YYYY-MM-DD HH:MM\n"
                "Examples: DAILY 02:00, WEEKLY Mon 08:00, MONTHLY 1 09:00\n"
                "Requires: ophix-task-wts Tier 2 client"
            ),
            validator_class="ophix_tasks.validators.WtsValidator",
            enabled=False,
        ),
    ])


class Migration(migrations.Migration):

    dependencies = [
        ("ophix_tasks", "0004_task_output_handling"),
    ]

    operations = [
        migrations.CreateModel(
            name="Scheduler",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(
                    help_text="Internal identifier used by Tier 2 clients (e.g. 'cron', 'systemd', 'wts').",
                    max_length=50,
                    unique=True,
                    verbose_name="name",
                )),
                ("label", models.CharField(
                    help_text="Human-readable name shown in admin (e.g. 'Cron (/etc/cron.d)').",
                    max_length=100,
                    verbose_name="label",
                )),
                ("interval_help", models.TextField(
                    blank=True,
                    default="",
                    help_text="Documentation shown to operators when setting the interval field.",
                    verbose_name="interval help",
                )),
                ("validator_class", models.CharField(
                    blank=True,
                    default="",
                    help_text="Dotted Python path to the validator class (e.g. 'ophix_tasks.validators.CronValidator').",
                    max_length=200,
                    verbose_name="validator class",
                )),
                ("enabled", models.BooleanField(
                    default=True,
                    help_text="Disabled schedulers cannot be selected on new tasks.",
                    verbose_name="enabled",
                )),
            ],
            options={
                "verbose_name": "Scheduler",
                "verbose_name_plural": "Schedulers",
                "ordering": ("name",),
            },
        ),
        migrations.AddField(
            model_name="scheduledtask",
            name="scheduler",
            field=models.ForeignKey(
                blank=True,
                help_text="Target scheduling system. Determines the expected interval format.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="tasks",
                to="ophix_tasks.scheduler",
                verbose_name="scheduler",
            ),
        ),
        migrations.RunPython(populate_schedulers, migrations.RunPython.noop),
    ]
