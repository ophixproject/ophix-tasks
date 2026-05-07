from rest_framework import serializers
from .models import ScheduledTask


class ScheduledTaskSerializer(serializers.ModelSerializer):
    schedule = serializers.CharField(source="schedule.name")

    class Meta:
        model = ScheduledTask
        fields = ["id", "schedule", "name", "command", "run_at", "interval", "starts_at", "ends_at"]
