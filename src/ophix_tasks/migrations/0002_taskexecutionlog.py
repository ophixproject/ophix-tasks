from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("ophix_core", "0001_initial"),
        ("ophix_tasks", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="TaskExecutionLog",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                (
                    "task",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="execution_logs",
                        to="ophix_tasks.scheduledtask",
                        verbose_name="task",
                    ),
                ),
                (
                    "client",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="ophix_core.client",
                        verbose_name="client",
                    ),
                ),
                ("reported_at", models.DateTimeField(auto_now_add=True, verbose_name="reported at")),
                ("output", models.TextField(blank=True, default="", verbose_name="output")),
            ],
            options={
                "verbose_name": "Task Execution Log",
                "verbose_name_plural": "Task Execution Logs",
                "ordering": ("-reported_at",),
            },
        ),
    ]
