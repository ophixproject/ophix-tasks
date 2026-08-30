"""
ophix_tasks.admin
~~~~~~~~~~~~~~~~~
Admin registrations for Scheduler, Schedule, ScheduledTask,
ClientScheduleAccess, and TaskExecutionLog.
"""

from django.contrib import admin
from django.conf import settings
from django import forms
from django.db import models
from django.contrib.admin.widgets import AdminSplitDateTime
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import path, reverse
from django.utils.html import format_html, mark_safe
from django.utils.timezone import localtime
from django.utils.translation import gettext_lazy as _

from ophix.core.admin import CleanSaveMessageMixin, DeleteRedirectToChangelistMixin
from admin_interface.widgets import Select2Widget
from .models import (
    Scheduler, Schedule, ScheduledTask, ClientScheduleAccess, TaskExecutionLog,
)


# ============================================================
# Custom widgets
# ============================================================

class SchedulerSelect(forms.Select):
    """Select widget that embeds interval_help as a data attribute on each option."""
    def create_option(self, name, value, label, selected, index, **kwargs):
        option = super().create_option(name, value, label, selected, index, **kwargs)
        if value:
            pk = value.value if hasattr(value, "value") else value
            try:
                scheduler = Scheduler.objects.get(pk=pk)
                if scheduler.interval_help:
                    option["attrs"]["data-interval-help"] = scheduler.interval_help
            except (Scheduler.DoesNotExist, ValueError, TypeError):
                pass
        return option


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
    fields = ("edit_link", "enabled", "paused", "name", "command_col", "timing_col", "output_col")
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
        return (cmd[:120] + "…") if len(cmd) > 120 else cmd
    command_col.short_description = _("Command")

    def timing_col(self, obj):
        if obj.run_at:
            return "once at {}".format(localtime(obj.run_at).strftime("%Y-%m-%d %H:%M"))
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
    fields = ("schedule", "enabled", "paused", "can_update", "notes")
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
    fields = ("client", "enabled", "paused", "can_update", "notes")
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
                    "• <span style='color: var(--admin-interface-disabled-color); font-weight: 600;'>{}</span>",
                    label,
                )
            )

    return format_html(
        "<div style='display: flex; flex-wrap: wrap; gap: 0.5em; white-space: normal;'>{}</div>",
        mark_safe(" ".join(items)),
    )

linked_schedules.short_description = _("Authorised Schedules")


# ============================================================
# SchedulerAdmin (shown only when SHOW_SCHEDULERS_MODEL is True)
# ============================================================

if getattr(settings, "SHOW_SCHEDULERS_MODEL", False):

    @admin.register(Scheduler)
    class SchedulerAdmin(CleanSaveMessageMixin, admin.ModelAdmin):
        menu_order = 50
        list_display = ("name", "label", "enabled", "validator_class")
        list_editable = ("enabled",)
        list_filter = ("enabled",)
        search_fields = ("name", "label")
        ordering = ("name",)
        actions = None
        fieldsets = [
            (None, {
                "fields": ["name", "label", "enabled"],
            }),
            (_("Interval"), {
                "fields": ["interval_help", "validator_class"],
            }),
        ]
        formfield_overrides = {
            models.TextField: {"widget": forms.Textarea(attrs={"rows": 4, "cols": 80})},
        }


# ============================================================
# ScheduleAdmin
# ============================================================

@admin.register(Schedule)
class ScheduleAdmin(CleanSaveMessageMixin, admin.ModelAdmin):
    menu_order = 100
    list_display = ("name", "description", "task_count", "enabled", "paused", "linked_clients")
    list_editable = ("enabled", "paused")
    list_filter = ("enabled", "paused")
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
                        "• <span style='color: var(--admin-interface-disabled-color); font-weight: 600;'>{}</span>",
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
class ScheduledTaskAdmin(CleanSaveMessageMixin, admin.ModelAdmin):
    menu_order = 200
    list_display = (
        "name", "schedule", "scheduler", "command_short", "description_short",
        "run_at", "interval", "enabled", "paused",
        "stdout_handling", "stderr_handling",
    )
    list_editable = ("enabled", "paused")
    list_filter = ("schedule", "scheduler", "enabled", "paused", TimingTypeFilter, "stdout_handling", "stderr_handling")
    search_fields = ("name", "command", "description", "schedule__name")
    ordering = ("schedule__name", "name")
    autocomplete_fields = ("schedule",)
    actions = None
    fieldsets = [
        (None, {
            "fields": ["name", "schedule", "scheduler", "enabled", "paused", "description", "command"],
        }),
        (_("Schedule"), {
            "fields": ["run_at", "interval", "starts_at", "ends_at"],
        }),
        (_("Output handling"), {
            "fields": ["stdout_handling", "stderr_handling", "log_file"],
        }),
    ]
    formfield_overrides = {
        # A plain forms.Textarea (not Django's AdminTextareaWidget) never gets the
        # vLargeTextField CSS class, so nothing caps its width — cols=100 alone gives
        # the browser a huge intrinsic size with no ceiling. admin.css used to
        # compensate with a percentage-based `width: 125%` hack tuned against the
        # container's width at the time it was written; that's now removed in favor
        # of this explicit inline width, sized to comfortably fit a long rsync-style
        # command after subtracting the nav sidebar and label column from a
        # 1920px-wide screen. An inline style here always wins over any external
        # stylesheet rule, so no interaction with admin.css to worry about.
        models.TextField: {"widget": forms.Textarea(attrs={"rows": 3, "cols": 100, "style": "width: 1240px;"})},
        models.DateTimeField: {"widget": AdminSplitDateTime(attrs={"style": "width: auto;"})},
    }

    class Media:
        css = {"all": ("ophix_tasks/admin.css",)}
        js = ("ophix_tasks/admin.js",)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        from django.contrib.admin.widgets import RelatedFieldWidgetWrapper
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if isinstance(getattr(formfield, "widget", None), RelatedFieldWidgetWrapper):
            formfield.widget.can_add_related = False
            formfield.widget.can_change_related = False
            formfield.widget.can_delete_related = False
            formfield.widget.can_view_related = False
        return formfield

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "scheduler":
            qs = Scheduler.objects.filter(enabled=True)
            obj_id = request.resolver_match.kwargs.get("object_id")
            if obj_id:
                try:
                    current = ScheduledTask.objects.get(pk=obj_id)
                    if current.scheduler_id:
                        qs = (qs | Scheduler.objects.filter(pk=current.scheduler_id)).distinct()
                except ScheduledTask.DoesNotExist:
                    pass
            kwargs["queryset"] = qs
            kwargs["widget"] = SchedulerSelect
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        kwargs.setdefault("widget", Select2Widget)
        return super().formfield_for_choice_field(db_field, request, **kwargs)

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        dup_pk = request.GET.get("_duplicate_from")
        if dup_pk:
            try:
                src = ScheduledTask.objects.get(pk=int(dup_pk))
                initial.update({
                    "schedule": src.schedule_id,
                    "scheduler": src.scheduler_id,
                    "name": src.name,
                    "command": src.command,
                    "description": src.description,
                    "interval": src.interval,
                    "run_at": src.run_at,
                    "starts_at": src.starts_at,
                    "ends_at": src.ends_at,
                    "enabled": src.enabled,
                    "paused": src.paused,
                    "stdout_handling": src.stdout_handling,
                    "stderr_handling": src.stderr_handling,
                    "log_file": src.log_file,
                })
            except (ScheduledTask.DoesNotExist, ValueError, TypeError):
                pass
        return initial

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:pk>/toggle/",
                self.admin_site.admin_view(self.toggle_view),
                name="ophix_tasks_scheduledtask_toggle",
            ),
            path(
                "<int:pk>/duplicate/",
                self.admin_site.admin_view(self.duplicate_view),
                name="ophix_tasks_scheduledtask_duplicate",
            ),
        ]
        return custom + urls

    def duplicate_view(self, request, pk):
        from django.contrib import messages
        messages.info(request, _("This is a copy of an existing task — edit the record, then save to create it."))
        add_url = reverse("admin:ophix_tasks_scheduledtask_add")
        return HttpResponseRedirect(f"{add_url}?_duplicate_from={pk}")

    def toggle_view(self, request, pk):
        if request.method != "POST":
            return JsonResponse({"ok": False}, status=405)
        field = request.POST.get("field")
        if field not in ("enabled", "paused"):
            return JsonResponse({"ok": False, "error": "invalid field"}, status=400)
        value = request.POST.get("value") == "1"
        updated = ScheduledTask.objects.filter(pk=pk).update(**{field: value})
        if not updated:
            return JsonResponse({"ok": False, "error": "not found"}, status=404)
        return JsonResponse({"ok": True})

    def command_short(self, obj):
        cmd = obj.command
        return (cmd[:120] + "…") if len(cmd) > 120 else cmd
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
    class ClientScheduleAccessAdmin(CleanSaveMessageMixin, admin.ModelAdmin):
        menu_order = 400
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
class TaskExecutionLogAdmin(DeleteRedirectToChangelistMixin, admin.ModelAdmin):
    menu_order = 500
    list_display = ("task", "client", "reported_at", "stream", "output_short")
    list_filter = (
        ("reported_at", admin.DateFieldListFilter),
        "stream",
        "task__schedule",
        "task",
        "client",
    )
    search_fields = ("task__name", "client__name", "output")
    ordering = ("-reported_at",)
    date_hierarchy = "reported_at"
    readonly_fields = ("task", "client", "reported_at", "stream", "output")
    actions = None

    def output_short(self, obj):
        return (obj.output[:80] + "…") if len(obj.output) > 80 else obj.output
    output_short.short_description = _("Output")

    class Media:
        css = {"all": ("ophix_tasks/admin.css",)}

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
