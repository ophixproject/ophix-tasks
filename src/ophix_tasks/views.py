"""
ophix_tasks.views
~~~~~~~~~~~~~~~~~
API views for the Task Scheduling domain plugin.

GET /api/tasks/
    Returns all tasks for the client's active schedule, including disabled
    tasks (marked enabled=False) so Tier 2 clients can comment them out
    rather than silently removing them. Time bounds (starts_at/ends_at)
    are still enforced server-side. If the schedule or access record is
    disabled, no tasks are returned.

POST /api/tasks/
    Creates a task in a schedule the client has can_update access to.
    Skips if a task with the same command already exists in that schedule.
    Returns {"status": "created"|"skipped", "id": <int>}.

POST /api/tasks/<id>/report/
    Receives execution output from a Tier 1 client and stores it in
    TaskExecutionLog. Body: {"output": "<text>"}.
"""

from django.db.models import Q
from django.utils import timezone

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from ophix.core.auth import ClientTokenAuthentication
from ophix.core.audit import record_access

from .models import ClientScheduleAccess, ScheduledTask, TaskExecutionLog
from .serializers import ScheduledTaskSerializer, TaskCreateSerializer


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

        # Include disabled tasks so Tier 2 clients can comment them out.
        # Time bounds and schedule/access enablement are still enforced.
        tasks = ScheduledTask.objects.filter(
            schedule_id__in=schedule_ids,
        ).filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=now),
            Q(ends_at__isnull=True) | Q(ends_at__gte=now),
        ).select_related("schedule")

        for access in access_qs:
            record_access(access, "GET")

        return Response(ScheduledTaskSerializer(tasks, many=True).data)

    def post(self, request):
        client = request.user

        serializer = TaskCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        try:
            access = ClientScheduleAccess.objects.select_related("schedule").get(
                client=client,
                schedule__name=data["schedule"],
                enabled=True,
                can_update=True,
                schedule__enabled=True,
            )
        except ClientScheduleAccess.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        existing = ScheduledTask.objects.filter(
            schedule=access.schedule,
            command=data["command"],
        ).first()

        if existing:
            return Response({"status": "skipped", "id": existing.pk}, status=status.HTTP_200_OK)

        task = ScheduledTask.objects.create(
            schedule=access.schedule,
            name=data["name"],
            command=data["command"],
            description=data.get("description", ""),
            interval=data.get("interval", ""),
            run_at=data.get("run_at"),
            starts_at=data.get("starts_at"),
            ends_at=data.get("ends_at"),
            stdout_handling=data.get("stdout_handling", "inherit"),
            stderr_handling=data.get("stderr_handling", "inherit"),
            log_file=data.get("log_file", ""),
        )

        record_access(access, "POST")
        return Response({"status": "created", "id": task.pk}, status=status.HTTP_201_CREATED)


class TaskReportView(APIView):
    authentication_classes = [ClientTokenAuthentication]

    def post(self, request, task_id):
        client = request.user

        try:
            task = ScheduledTask.objects.select_related("schedule").get(pk=task_id)
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
