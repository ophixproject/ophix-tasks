"""
ophix_tasks.models
~~~~~~~~~~~~~~~~~~
Domain models for the Ophix Task Scheduling server.

Scheduler
    A named scheduler type (e.g. "cron", "systemd", "wts"). Stores a
    validator class reference that is used to validate the interval field
    on ScheduledTask. Operators can disable schedulers they don't support.

Schedule
    A named collection of tasks. This is the artifact — clients are
    granted access at this level and receive all active tasks within it.

ScheduledTask
    An individual task entry within a Schedule. Defines what to run
    and when. Exactly one of run_at (one-off) or interval (recurring)
    must be set. The scheduler field identifies the target scheduling
    system and governs interval format validation.

ClientScheduleAccess
    Join table linking a Client to a Schedule with per-link permission
    flags inherited from ClientArtifactBase.
"""

import importlib

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from ophix.core.models import ClientArtifactBase


STDOUT_CHOICES = [
    ("inherit", "Default (scheduler handles output)"),
    ("report", "Report to server"),
    ("null", "Discard (/dev/null)"),
    ("file", "Append to log file"),
]

STDERR_CHOICES = [
    ("inherit", "Default (scheduler handles errors)"),
    ("report", "Report to server"),
    ("null", "Discard (/dev/null)"),
    ("merge", "Merge with stdout (2>&1)"),
    ("file", "Append to log file"),
]


class Scheduler(models.Model):
    name = models.CharField(
        _("name"),
        max_length=50,
        unique=True,
        help_text=_("Internal identifier used by Tier 2 clients (e.g. 'cron', 'systemd', 'wts')."),
    )
    label = models.CharField(
        _("label"),
        max_length=100,
        help_text=_("Human-readable name shown in admin (e.g. 'Cron (/etc/cron.d)')."),
    )
    interval_help = models.TextField(
        _("interval help"),
        blank=True,
        default="",
        help_text=_("Documentation shown to operators when setting the interval field."),
    )
    validator_class = models.CharField(
        _("validator class"),
        max_length=200,
        blank=True,
        default="",
        help_text=_("Dotted Python path to the validator class (e.g. 'ophix_tasks.validators.CronValidator')."),
    )
    enabled = models.BooleanField(
        _("enabled"),
        default=True,
        help_text=_("Disabled schedulers cannot be selected on new tasks."),
    )

    class Meta:
        ordering = ("name",)
        verbose_name = _("Scheduler")
        verbose_name_plural = _("Schedulers")

    def __str__(self):
        return self.label or self.name


class Schedule(models.Model):
    name = models.CharField(_("name"), max_length=100, unique=True)
    description = models.TextField(_("description"), blank=True, default="")
    enabled = models.BooleanField(_("enabled"), default=True)
    paused = models.BooleanField(
        _("paused"),
        default=False,
        help_text=_("Pause all tasks in this schedule for all clients. Tasks remain visible in responses but are marked paused."),
    )
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
    scheduler = models.ForeignKey(
        Scheduler,
        verbose_name=_("scheduler"),
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="tasks",
        help_text=_("Target scheduling system. Determines the expected interval format."),
    )
    name = models.CharField(_("name"), max_length=200)
    command = models.TextField(_("command"))
    description = models.TextField(
        _("description"),
        blank=True,
        default="",
        help_text=_("Optional note written as a comment in the generated schedule file."),
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
        help_text=_("Recurring task: interval expression for the assigned scheduler. Leave blank for a one-off task."),
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
    paused = models.BooleanField(
        _("paused"),
        default=False,
        help_text=_("Pause this task for all clients. The task remains in responses but is marked paused."),
    )

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

    def clean(self):
        if self.run_at and self.interval:
            raise ValidationError(
                _("Set either 'run at' for a one-off task or 'interval' for a recurring task, not both.")
            )
        if self.interval and self.scheduler_id:
            scheduler = self.scheduler
            if scheduler.validator_class:
                try:
                    module_path, class_name = scheduler.validator_class.rsplit(".", 1)
                    module = importlib.import_module(module_path)
                    validator_cls = getattr(module, class_name)
                    validator_cls.validate(self.interval)
                except ValidationError:
                    raise
                except Exception as exc:
                    raise ValidationError(
                        _("Interval validation error: {}").format(exc)
                    )

    class Meta:
        ordering = ("schedule__name", "name")
        verbose_name = _("Scheduled Task")
        verbose_name_plural = _("Scheduled Tasks")

    def __str__(self):
        return "{} / {}".format(self.schedule.name, self.name)


STREAM_CHOICES = [
    ("stdout", "stdout only"),
    ("stderr", "stderr only"),
    ("both", "stdout + stderr"),
]


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
    stream = models.CharField(
        _("stream"),
        max_length=6,
        choices=STREAM_CHOICES,
        default="both",
        help_text=_("Which output stream(s) were captured."),
    )
    output = models.TextField(_("output"), blank=True, default="")

    class Meta:
        ordering = ("-reported_at",)
        verbose_name = _("Execution Log")
        verbose_name_plural = _("Execution Logs")

    def __str__(self):
        return "{} @ {}".format(self.task, self.reported_at)


class ClientScheduleAccess(ClientArtifactBase):
    schedule = models.ForeignKey(
        Schedule,
        verbose_name=_("schedule"),
        on_delete=models.CASCADE,
        related_name="client_access",
    )
    paused = models.BooleanField(
        _("paused"),
        default=False,
        help_text=_("Pause all tasks in this schedule for this client only. Tasks remain visible in responses but are marked paused."),
    )

    class Meta:
        unique_together = ("client", "schedule")
        verbose_name = _("Client Schedule Access")
        verbose_name_plural = _("Client Schedule Access")

    def __str__(self):
        return "{} → {}".format(self.client, self.schedule.name)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
