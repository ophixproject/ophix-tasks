from rest_framework import serializers
from .models import ScheduledTask, STDOUT_CHOICES, STDERR_CHOICES


class ScheduledTaskSerializer(serializers.ModelSerializer):
    schedule = serializers.CharField(source="schedule.name")
    scheduler = serializers.SerializerMethodField()
    paused = serializers.SerializerMethodField()

    class Meta:
        model = ScheduledTask
        fields = [
            "id", "schedule", "scheduler", "name", "command", "description",
            "run_at", "interval", "starts_at", "ends_at", "enabled", "paused",
            "stdout_handling", "stderr_handling", "log_file",
        ]

    def get_scheduler(self, obj):
        return obj.scheduler.name if obj.scheduler_id else None

    def get_paused(self, obj):
        # The view sets _paused to the effective paused state (task + schedule + access).
        # Fall back to the task's own paused field if not set by the view.
        return getattr(obj, "_paused", obj.paused)


class TaskCreateSerializer(serializers.Serializer):
    schedule = serializers.CharField()
    scheduler = serializers.CharField(allow_blank=True, required=False, default="")
    name = serializers.CharField(max_length=200)
    command = serializers.CharField()
    description = serializers.CharField(allow_blank=True, default="")
    interval = serializers.CharField(allow_blank=True, default="")
    run_at = serializers.DateTimeField(allow_null=True, required=False, default=None)
    starts_at = serializers.DateTimeField(allow_null=True, required=False, default=None)
    ends_at = serializers.DateTimeField(allow_null=True, required=False, default=None)
    stdout_handling = serializers.ChoiceField(
        choices=[c[0] for c in STDOUT_CHOICES], default="inherit"
    )
    stderr_handling = serializers.ChoiceField(
        choices=[c[0] for c in STDERR_CHOICES], default="inherit"
    )
    log_file = serializers.CharField(allow_blank=True, default="")
