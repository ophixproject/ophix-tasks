from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class OphixTasksConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ophix_tasks"
    verbose_name = _("Tasks")
    admin_order = 240
    is_ophix_domain = True

    def ready(self):
        from ophix.core.admin import ClientAdmin
        from .admin import ClientScheduleInlineForClient, linked_schedules
        ClientAdmin.register_inline(ClientScheduleInlineForClient)
        ClientAdmin.register_column(linked_schedules)
