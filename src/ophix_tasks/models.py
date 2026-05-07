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
    flags inherited from ClientArtifactBase.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from ophix.core.models import ClientArtifactBase


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

    # Scheduling — exactly one of run_at or interval must be set.
    run_at = models.DateTimeField(
        _("run at"),
        null=True,
        blank=True,
        help_text=_(
            "One-off: exact UTC datetime to run. "
            "Mutually exclusive with interval."
        ),
    )
    interval = models.CharField(
        _("interval"),
        max_length=100,
        blank=True,
        default="",
        help_text=_(
            "Recurring: cron expression (e.g. '0 2 * * *'). "
            "Mutually exclusive with run_at."
        ),
    )

    # Time bounds — enforced server-side by filtering the API response.
    starts_at = models.DateTimeField(
        _("starts at"),
        null=True,
        blank=True,
        help_text=_("Do not include in responses before this UTC datetime."),
    )
    ends_at = models.DateTimeField(
        _("ends at"),
        null=True,
        blank=True,
        help_text=_("Stop including in responses after this UTC datetime."),
    )

    enabled = models.BooleanField(_("enabled"), default=True)

    # Reporting — server controls whether stdout/stderr are captured and stored.
    report_output = models.BooleanField(
        _("report output"),
        default=False,
        help_text=_("Capture stdout and store in the execution log."),
    )
    report_error = models.BooleanField(
        _("report errors"),
        default=False,
        help_text=_("Capture stderr and store in the execution log."),
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
