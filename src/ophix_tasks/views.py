"""
ophix_tasks.views
~~~~~~~~~~~~~~~~~
API views for the Task Scheduling domain plugin.

GET /api/tasks/
    Returns tasks for the client's enabled schedules. Pass ?schedule=name to
    restrict to one schedule; pass ?scheduler=name to restrict to tasks for a
    specific scheduler type (e.g. ?scheduler=cron returns only cron tasks).
    Disabled tasks are included so Tier 2 clients can comment them out.
    Time bounds (starts_at/ends_at) are enforced server-side.

POST /api/tasks/
    Creates a task in a schedule the client has can_update access to.
    Skips if a task with the same command already exists in that schedule.
    Returns {"status": "created"|"skipped", "id": <int>}.

POST /api/tasks/<id>/report/
    Receives execution output and stores it in TaskExecutionLog.
    Body: {"output": "<text>"}.
"""

from django.db.models import Q
from django.utils import timezone

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from ophix.core.auth import ClientTokenAuthentication
from ophix.core.audit import record_access

from .models import ClientScheduleAccess, Schedule, Scheduler, ScheduledTask, TaskExecutionLog
from .serializers import ScheduledTaskSerializer, TaskCreateSerializer


class TaskListView(APIView):
    authentication_classes = [ClientTokenAuthentication]

    def get(self, request):
        client = request.user
        now = timezone.now()
        schedule_name = request.query_params.get("schedule")
        scheduler_name = request.query_params.get("scheduler")

        access_filter = ClientScheduleAccess.objects.filter(
            client=client,
            enabled=True,
            schedule__enabled=True,
        )
        if schedule_name:
            access_filter = access_filter.filter(schedule__name=schedule_name)

        access_qs = list(access_filter.select_related("schedule"))
        schedule_ids = [a.schedule_id for a in access_qs]

        tasks = ScheduledTask.objects.filter(
            schedule_id__in=schedule_ids,
        ).filter(
            Q(starts_at__isnull=True) | Q(starts_at__lte=now),
            Q(ends_at__isnull=True) | Q(ends_at__gte=now),
        ).select_related("schedule", "scheduler")

        if scheduler_name:
            tasks = tasks.filter(scheduler__name=scheduler_name)

        for access in access_qs:
            record_access(access, "GET")

        return Response(ScheduledTaskSerializer(tasks, many=True).data)

    def post(self, request):
        client = request.user

        serializer = TaskCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        schedule_name = data["schedule"]
        schedule_created = False

        try:
            access = ClientScheduleAccess.objects.select_related("schedule").get(
                client=client,
                schedule__name=schedule_name,
                enabled=True,
                can_update=True,
                schedule__enabled=True,
            )
        except ClientScheduleAccess.DoesNotExist:
            # If the schedule doesn't exist at all, auto-create it and grant access.
            # If it exists but this client lacks permission, refuse — explicit grant required.
            if Schedule.objects.filter(name=schedule_name).exists():
                return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
            schedule = Schedule.objects.create(name=schedule_name)
            access = ClientScheduleAccess.objects.create(
                client=client,
                schedule=schedule,
                enabled=True,
                can_update=True,
            )
            schedule_created = True

        existing = ScheduledTask.objects.filter(
            schedule=access.schedule,
            command=data["command"],
        ).first()

        if existing:
            return Response({"status": "skipped", "id": existing.pk}, status=status.HTTP_200_OK)

        scheduler = None
        scheduler_name = data.get("scheduler", "")
        if scheduler_name:
            try:
                scheduler = Scheduler.objects.get(name=scheduler_name)
            except Scheduler.DoesNotExist:
                return Response(
                    {"scheduler": ["Unknown scheduler: {!r}".format(scheduler_name)]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        task = ScheduledTask.objects.create(
            schedule=access.schedule,
            scheduler=scheduler,
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
        return Response(
            {"status": "created", "id": task.pk, "schedule_created": schedule_created},
            status=status.HTTP_201_CREATED,
        )


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
