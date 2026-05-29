from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("ophix_tasks", "0008_taskexecutionlog_stream"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="taskexecutionlog",
            options={
                "ordering": ["-reported_at"],
                "verbose_name": "Execution Log",
                "verbose_name_plural": "Execution Logs",
            },
        ),
    ]
