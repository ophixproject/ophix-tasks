"""
ophix_tasks.admin
~~~~~~~~~~~~~~~~~
Admin registrations for Schedule, ScheduledTask, and ClientScheduleAccess.
"""

from django.contrib import admin
from django.conf import settings
from django import forms
from django.db import models
from django.contrib.admin.widgets import AdminSplitDateTime
from django.utils.html import format_html, mark_safe
from django.utils.translation import gettext_lazy as _

from .models import Schedule, ScheduledTask, ClientScheduleAccess, TaskExecutionLog


# ============================================================
# Inlines
# ============================================================

class ScheduledTaskInline(admin.TabularInline):
    model = ScheduledTask
    extra = 1
    fields = ("name", "command", "run_at", "interval", "starts_at", "ends_at", "enabled", "report_output", "report_error")
    classes = ("collapse",)
    formfield_overrides = {
        models.TextField: {"widget": forms.Textarea(attrs={"rows": 2, "cols": 60})},
        models.DateTimeField: {"widget": AdminSplitDateTime(attrs={"style": "width: auto;"})},
    }

    class Media:
        css = {"all": ("ophix_tasks/admin.css",)}


class ClientScheduleInlineForClient(admin.TabularInline):
    """Shown on Client admin — registered via AppConfig.ready()."""
    model = ClientScheduleAccess
    extra = 0
    autocomplete_fields = ("schedule",)
    fields = ("schedule", "enabled", "notes")
    classes = ("collapse",)
    verbose_name = _("Schedule")
    verbose_name_plural = _("Schedules")
    formfield_overrides = {
        models.TextField: {"widget": forms.Textarea(attrs={"rows": 2, "cols": 120})},
    }


class ClientScheduleInlineForSchedule(admin.TabularInline):
    """Shown on Schedule admin — manage which clients can fetch this schedule."""
    model = ClientScheduleAccess
    extra = 0
    autocomplete_fields = ("client",)
    fields = ("client", "enabled", "notes")
    classes = ("collapse",)
    verbose_name = _("Client")
    verbose_name_plural = _("Clients")
    formfield_overrides = {
        models.TextField: {"widget": forms.Textarea(attrs={"rows": 2, "cols": 120})},
    }


# ============================================================
# ClientAdmin column — contributed via register_column()
# ============================================================

def linked_schedules(self, obj):
    links = ClientScheduleAccess.objects.filter(client=obj).select_related("schedule")
    if not links:
        return "—"

    items = []
    for cs in links:
        label = cs.schedule.name
        if cs.enabled and cs.schedule.enabled:
            items.append(f"• {label}")
        else:
            items.append(
                format_html(
                    "• <span style='color: color-mix(in srgb, var(--admin-interface-delete-button-background-color) 60%, currentColor 40%); font-style: italic;'>{}</span>",
                    label,
                )
            )

    return format_html(
        "<div style='display: flex; flex-wrap: wrap; gap: 0.5em; white-space: normal;'>{}</div>",
        mark_safe(" ".join(items)),
    )

linked_schedules.short_description = _("Authorised Schedules")


# ============================================================
# ScheduleAdmin
# ============================================================

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "task_count", "enabled", "linked_clients")
    list_editable = ("enabled",)
    list_filter = ("enabled",)
    search_fields = ("name", "description")
    ordering = ("name",)
    readonly_fields = ("updated_at",)
    inlines = [ScheduledTaskInline, ClientScheduleInlineForSchedule]
    actions = None

    def task_count(self, obj):
        return obj.tasks.count()
    task_count.short_description = _("Tasks")

    def linked_clients(self, obj):
        links = obj.client_access.select_related("client")
        if not links:
            return "—"

        items = []
        for cs in links:
            label = cs.client.name
            if cs.enabled and cs.client.enabled:
                items.append(f"• {label}")
            else:
                items.append(
                    format_html(
                        "• <span style='color: color-mix(in srgb, var(--admin-interface-delete-button-background-color) 60%, currentColor 40%); font-style: italic;'>{}</span>",
                        label,
                    )
                )

        return format_html(
            "<div style='display: flex; flex-wrap: wrap; gap: 0.5em; white-space: normal;'>{}</div>",
            mark_safe(" ".join(items)),
        )

    linked_clients.short_description = _("Authorised Clients")


# ============================================================
# ScheduledTaskAdmin — granular task-level editing
# ============================================================

@admin.register(ScheduledTask)
class ScheduledTaskAdmin(admin.ModelAdmin):
    list_display = ("name", "schedule", "command_short", "run_at", "interval", "starts_at", "ends_at", "enabled", "report_output", "report_error")
    list_editable = ("enabled", "report_output", "report_error")
    list_filter = ("enabled", "report_output", "report_error", "schedule")
    search_fields = ("name", "command", "schedule__name")
    ordering = ("schedule__name", "name")
    autocomplete_fields = ("schedule",)
    actions = None
    formfield_overrides = {
        models.TextField: {"widget": forms.Textarea(attrs={"rows": 3, "cols": 120})},
        models.DateTimeField: {"widget": AdminSplitDateTime(attrs={"style": "width: auto;"})},
    }

    class Media:
        css = {"all": ("ophix_tasks/admin.css",)}

    def command_short(self, obj):
        cmd = obj.command
        return (cmd[:60] + "…") if len(cmd) > 60 else cmd
    command_short.short_description = _("Command")


# ============================================================
# ClientScheduleAccess admin (optional)
# ============================================================

if getattr(settings, "SHOW_CLIENT_ARTIFACT_MODEL", False):

    @admin.register(ClientScheduleAccess)
    class ClientScheduleAccessAdmin(admin.ModelAdmin):
        list_display = ("client", "schedule", "enabled", "short_notes")
        list_editable = ("enabled",)
        list_filter = ("enabled", "client__host", "client", "schedule")
        search_fields = ("client__name", "schedule__name", "notes")
        actions = None

        def short_notes(self, obj):
            return (obj.notes[:50] + "…") if obj.notes and len(obj.notes) > 50 else obj.notes
        short_notes.short_description = _("Notes")


# ============================================================
# TaskExecutionLog admin — read-only
# ============================================================

@admin.register(TaskExecutionLog)
class TaskExecutionLogAdmin(admin.ModelAdmin):
    list_display = ("task", "client", "reported_at", "output_short")
    list_filter = ("task__schedule", "task", "client")
    search_fields = ("task__name", "client__name", "output")
    ordering = ("-reported_at",)
    readonly_fields = ("task", "client", "reported_at", "output")
    actions = None

    def output_short(self, obj):
        return (obj.output[:80] + "…") if len(obj.output) > 80 else obj.output
    output_short.short_description = _("Output")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
