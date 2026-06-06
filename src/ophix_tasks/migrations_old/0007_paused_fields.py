from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ophix_tasks", "0006_alter_scheduledtask_description_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="schedule",
            name="paused",
            field=models.BooleanField(
                default=False,
                help_text="Pause all tasks in this schedule for all clients. Tasks remain visible in responses but are marked paused.",
                verbose_name="paused",
            ),
        ),
        migrations.AddField(
            model_name="scheduledtask",
            name="paused",
            field=models.BooleanField(
                default=False,
                help_text="Pause this task for all clients. The task remains in responses but is marked paused.",
                verbose_name="paused",
            ),
        ),
        migrations.AddField(
            model_name="clientscheduleaccess",
            name="paused",
            field=models.BooleanField(
                default=False,
                help_text="Pause all tasks in this schedule for this client only. Tasks remain visible in responses but are marked paused.",
                verbose_name="paused",
            ),
        ),
    ]
