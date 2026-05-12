from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ophix_tasks", "0007_paused_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="taskexecutionlog",
            name="stream",
            field=models.CharField(
                choices=[("stdout", "stdout only"), ("stderr", "stderr only"), ("both", "stdout + stderr")],
                default="both",
                help_text="Which output stream(s) were captured.",
                max_length=6,
                verbose_name="stream",
            ),
        ),
    ]
