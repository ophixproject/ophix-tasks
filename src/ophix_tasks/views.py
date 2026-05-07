"""
ophix_tasks.views
~~~~~~~~~~~~~~~~~
API views for the Task Scheduling domain plugin.

GET /api/tasks/
    Returns a flat JSON array of all currently active tasks for the
    authenticated client, aggregated across all schedules the client
    has access to. Server-side time filtering (starts_at / ends_at)
    is applied here — Tier 2 clients receive only what is active now.

POST /api/tasks/<id>/report/
    Receives execution output from a Tier 1 client and stores it in
    TaskExecutionLog. The client must have access to the schedule that
    owns the task. Body: {"output": "<text>"}.
"""

from django.db.models import Q
from django.utils import timezone

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from ophix.core.auth import ClientTokenAuthentication
from ophix.core.audit import record_access

from .models import ClientScheduleAccess, ScheduledTask, TaskExecutionLog
from .serializers import ScheduledTaskSerializer


class TaskListView(APIView):
    authentication_classes = [ClientTokenAuthentication]

    def get(self, request):
        client = request.user
        now = timezone.now()

        access_qs = list(
            ClientScheduleAccess.objects.filter(
                client=client,
                enabled=True,
                schedule__enabled=True,
            ).select_related("schedule")
        )

        schedule_ids = [a.schedule_id for a in access_qs]

        tasks = ScheduledTask.objects.filter(
            schedule_id__in=schedule_ids,
            enabled=True,
        ).filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=now),
            Q(ends_at__isnull=True) | Q(ends_at__gte=now),
        ).select_related("schedule")

        for access in access_qs:
            record_access(access, "GET")

        return Response(ScheduledTaskSerializer(tasks, many=True).data)


class TaskReportView(APIView):
    authentication_classes = [ClientTokenAuthentication]

    def post(self, request, task_id):
        client = request.user

        try:
            task = ScheduledTask.objects.select_related("schedule").get(pk=task_id, enabled=True)
        except ScheduledTask.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        has_access = ClientScheduleAccess.objects.filter(
            client=client,
            schedule=task.schedule,
            enabled=True,
            schedule__enabled=True,
        ).exists()

        if not has_access:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        output = request.data.get("output", "")
        TaskExecutionLog.objects.create(task=task, client=client, output=output)

        return Response({"status": "ok"}, status=status.HTTP_201_CREATED)
