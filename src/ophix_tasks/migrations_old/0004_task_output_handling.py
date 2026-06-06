from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ophix_tasks", "0003_alter_clientscheduleaccess_can_delete_and_more"),
    ]

    operations = [
        migrations.RemoveField(model_name="scheduledtask", name="report_output"),
        migrations.RemoveField(model_name="scheduledtask", name="report_error"),
        migrations.AddField(
            model_name="scheduledtask",
            name="description",
            field=models.TextField(blank=True, default="", verbose_name="description"),
        ),
        migrations.AddField(
            model_name="scheduledtask",
            name="stdout_handling",
            field=models.CharField(
                choices=[
                    ("inherit", "Default (cron handles output)"),
                    ("report", "Report to server"),
                    ("null", "Discard (/dev/null)"),
                    ("file", "Append to log file"),
                ],
                default="inherit",
                max_length=10,
                verbose_name="stdout handling",
            ),
        ),
        migrations.AddField(
            model_name="scheduledtask",
            name="stderr_handling",
            field=models.CharField(
                choices=[
                    ("inherit", "Default (cron handles errors)"),
                    ("report", "Report to server"),
                    ("null", "Discard (/dev/null)"),
                    ("merge", "Merge with stdout (2>&1)"),
                    ("file", "Append to log file"),
                ],
                default="inherit",
                max_length=10,
                verbose_name="stderr handling",
            ),
        ),
        migrations.AddField(
            model_name="scheduledtask",
            name="log_file",
            field=models.CharField(blank=True, default="", max_length=500, verbose_name="log file"),
        ),
    ]
