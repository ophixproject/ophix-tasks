"""
ophix_tasks.models
~~~~~~~~~~~~~~~~~~
Domain models for the Ophix Task Scheduling server.

Schedule
    A named collection of tasks. This is the artifact — clients are
    granted access at this level and receive all active tasks within it.

ScheduledTask
    An individual task entry within a Schedule. Defines what to run
    and when. Exactly one of run_at (one-off) or interval (recurring)
    must be set. starts_at and ends_at are server-side time bounds —
    the server omits tasks outside their window from API responses.

ClientScheduleAccess
    Join table linking a Client to a Schedule with per-link permission
    flags inherited from ClientArtifactBase. Only one enabled access
    record is permitted per client at a time — enabling one automatically
    disables all others for the same client.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from ophix.core.models import ClientArtifactBase


STDOUT_CHOICES = [
    ("inherit", "Default (cron handles output)"),
    ("report", "Report to server"),
    ("null", "Discard (/dev/null)"),
    ("file", "Append to log file"),
]

STDERR_CHOICES = [
    ("inherit", "Default (cron handles errors)"),
    ("report", "Report to server"),
    ("null", "Discard (/dev/null)"),
    ("merge", "Merge with stdout (2>&1)"),
    ("file", "Append to log file"),
]


class Schedule(models.Model):
    name = models.CharField(_("name"), max_length=100, unique=True)
    description = models.TextField(_("description"), blank=True, default="")
    enabled = models.BooleanField(_("enabled"), default=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        ordering = ("name",)
        verbose_name = _("Schedule")
        verbose_name_plural = _("Schedules")

    def __str__(self):
        return self.name


class ScheduledTask(models.Model):
    schedule = models.ForeignKey(
        Schedule,
        verbose_name=_("schedule"),
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    name = models.CharField(_("name"), max_length=200)
    command = models.TextField(_("command"))
    description = models.TextField(
        _("description"),
        blank=True,
        default="",
        help_text=_("Optional note written as a comment above the cron entry."),
    )

    # Scheduling — exactly one of run_at or interval must be set.
    run_at = models.DateTimeField(
        _("run at"),
        null=True,
        blank=True,
        help_text=_("One-off task: the exact date and time to execute. Leave blank for a recurring task."),
    )
    interval = models.CharField(
        _("interval"),
        max_length=100,
        blank=True,
        default="",
        help_text=_("Recurring task: cron expression (e.g. '0 2 * * *'). Leave blank for a one-off task."),
    )

    # Time bounds — enforced server-side by filtering the API response.
    starts_at = models.DateTimeField(
        _("starts at"),
        null=True,
        blank=True,
        help_text=_("Do not include in responses before this date and time."),
    )
    ends_at = models.DateTimeField(
        _("ends at"),
        null=True,
        blank=True,
        help_text=_("Stop including in responses after this date and time."),
    )

    enabled = models.BooleanField(_("enabled"), default=True)

    # Output handling — server controls where stdout and stderr go.
    stdout_handling = models.CharField(
        _("stdout handling"),
        max_length=10,
        choices=STDOUT_CHOICES,
        default="inherit",
        help_text=_("Where to send standard output."),
    )
    stderr_handling = models.CharField(
        _("stderr handling"),
        max_length=10,
        choices=STDERR_CHOICES,
        default="inherit",
        help_text=_("Where to send standard error."),
    )
    log_file = models.CharField(
        _("log file"),
        max_length=500,
        blank=True,
        default="",
        help_text=_("Path to append output to when stdout or stderr handling is set to 'file'."),
    )

    class Meta:
        ordering = ("schedule__name", "name")
        verbose_name = _("Scheduled Task")
        verbose_name_plural = _("Scheduled Tasks")

    def __str__(self):
        return f"{self.schedule.name} / {self.name}"


class TaskExecutionLog(models.Model):
    task = models.ForeignKey(
        ScheduledTask,
        verbose_name=_("task"),
        on_delete=models.CASCADE,
        related_name="execution_logs",
    )
    client = models.ForeignKey(
        "ophix_core.Client",
        verbose_name=_("client"),
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
    )
    reported_at = models.DateTimeField(_("reported at"), auto_now_add=True)
    output = models.TextField(_("output"), blank=True, default="")

    class Meta:
        ordering = ("-reported_at",)
        verbose_name = _("Task Execution Log")
        verbose_name_plural = _("Task Execution Logs")

    def __str__(self):
        return "{} @ {}".format(self.task, self.reported_at)


class ClientScheduleAccess(ClientArtifactBase):
    schedule = models.ForeignKey(
        Schedule,
        verbose_name=_("schedule"),
        on_delete=models.CASCADE,
        related_name="client_access",
    )

    class Meta:
        unique_together = ("client", "schedule")
        verbose_name = _("Client Schedule Access")
        verbose_name_plural = _("Client Schedule Access")

    def __str__(self):
        return f"{self.client} → {self.schedule.name}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
