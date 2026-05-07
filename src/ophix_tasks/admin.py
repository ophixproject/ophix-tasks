"""
ophix_tasks.admin
~~~~~~~~~~~~~~~~~
Admin registrations for Schedule, ScheduledTask, ClientScheduleAccess,
and TaskExecutionLog.
"""

from django.contrib import admin
from django.conf import settings
from django import forms
from django.db import models
from django.contrib.admin.widgets import AdminSplitDateTime
from django.urls import reverse
from django.utils.html import format_html, mark_safe
from django.utils.translation import gettext_lazy as _

from .models import Schedule, ScheduledTask, ClientScheduleAccess, TaskExecutionLog


# ============================================================
# Custom filters
# ============================================================

class TimingTypeFilter(admin.SimpleListFilter):
    title = _("timing type")
    parameter_name = "timing"

    def lookups(self, request, model_admin):
        return [
            ("once", _("One-off (run at)")),
            ("recurring", _("Recurring (interval)")),
        ]

    def queryset(self, request, queryset):
        if self.value() == "once":
            return queryset.filter(run_at__isnull=False)
        if self.value() == "recurring":
            return queryset.filter(interval__isnull=False)
        return queryset


# ============================================================
# Inlines
# ============================================================

class ScheduledTaskInline(admin.TabularInline):
    model = ScheduledTask
    extra = 0
    show_change_link = False
    ordering = ("name",)
    fields = ("edit_link", "enabled", "name", "command_col", "timing_col", "output_col")
    readonly_fields = ("edit_link", "name", "command_col", "timing_col", "output_col")
    classes = ("collapse",)

    class Media:
        css = {"all": ("ophix_tasks/admin.css",)}
        js = ("ophix_tasks/admin.js",)

    def has_add_permission(self, request, obj=None):
        return False

    def edit_link(self, obj):
        if not obj.pk:
            return ""
        url = reverse("admin:ophix_tasks_scheduledtask_change", args=[obj.pk]) + "?_popup=1"
        return format_html(
            '<a class="changelink" href="{}" onclick="return showRelatedObjectPopup(this);">Edit</a>',
            url,
        )
    edit_link.short_description = ""

    def command_col(self, obj):
        cmd = obj.command
        return (cmd[:70] + "…") if len(cmd) > 70 else cmd
    command_col.short_description = _("Command")

    def timing_col(self, obj):
        if obj.run_at:
            return "once at {}".format(obj.run_at.strftime("%Y-%m-%d %H:%M"))
        return obj.interval or "—"
    timing_col.short_description = _("Timing")

    def output_col(self, obj):
        parts = []
        if obj.stdout_handling != "inherit":
            parts.append("out:{}".format(obj.stdout_handling))
        if obj.stderr_handling != "inherit":
            parts.append("err:{}".format(obj.stderr_handling))
        return ", ".join(parts) if parts else "—"
    output_col.short_description = _("Output")


class ClientScheduleInlineForClient(admin.TabularInline):
    """Shown on Client admin — registered via AppConfig.ready()."""
    model = ClientScheduleAccess
    extra = 0
    autocomplete_fields = ("schedule",)
    fields = ("schedule", "enabled", "can_update", "notes")
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
    fields = ("client", "enabled", "can_update", "notes")
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
            items.append("• {}".format(label))
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
                items.append("• {}".format(label))
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
    list_display = (
        "name", "schedule", "command_short", "description_short",
        "run_at", "interval", "enabled",
        "stdout_handling", "stderr_handling",
    )
    list_editable = ("enabled",)
    list_filter = ("schedule", "enabled", TimingTypeFilter, "stdout_handling", "stderr_handling")
    search_fields = ("name", "command", "description", "schedule__name")
    ordering = ("schedule__name", "name")
    autocomplete_fields = ("schedule",)
    actions = None
    fieldsets = [
        (None, {
            "fields": [("name", "schedule", "enabled"), "description", "command"],
        }),
        ("Schedule", {
            "fields": [("run_at", "interval"), ("starts_at", "ends_at")],
        }),
        ("Output handling", {
            "fields": [("stdout_handling", "stderr_handling"), "log_file"],
        }),
    ]
    formfield_overrides = {
        models.TextField: {"widget": forms.Textarea(attrs={"rows": 3, "cols": 100})},
        models.DateTimeField: {"widget": AdminSplitDateTime(attrs={"style": "width: auto;"})},
    }

    class Media:
        css = {"all": ("ophix_tasks/admin.css",)}

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not obj:
            schedule_id = request.GET.get("schedule")
            if schedule_id:
                try:
                    form.base_fields["schedule"].initial = int(schedule_id)
                except (ValueError, TypeError):
                    pass
        return form

    def command_short(self, obj):
        cmd = obj.command
        return (cmd[:60] + "…") if len(cmd) > 60 else cmd
    command_short.short_description = _("Command")

    def description_short(self, obj):
        if not obj.description:
            return ""
        return (obj.description[:50] + "…") if len(obj.description) > 50 else obj.description
    description_short.short_description = _("Description")


# ============================================================
# ClientScheduleAccess admin (optional)
# ============================================================

if getattr(settings, "SHOW_CLIENT_ARTIFACT_MODEL", False):

    @admin.register(ClientScheduleAccess)
    class ClientScheduleAccessAdmin(admin.ModelAdmin):
        list_display = ("client", "schedule", "enabled", "can_update", "short_notes")
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
