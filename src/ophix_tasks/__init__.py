plugin_category = "module"
plugin_sort = 130

default_app_config = "ophix_tasks.apps.OphixTasksConfig"


def install_configure(conf, command):
    """configure_install hook: contribute this domain's backup target."""
    existing = conf.get("backup", "targets_extra", fallback="")
    conf.set("backup", "targets_extra", ",".join(filter(None, [existing, "tasks"])))


def get_doc_tokens():
    """
    Optional hook discovered by ophix-docs (if installed), for {{ token }}
    substitution in shared markdown like the Client Quickstart doc.
    """
    return {
        "client_package": "ophix-task-client",
        "client_command": "task-client",
        "client_venv": ".task-env",
        "client_env": ".task.env",
        "client_env_prefix": "TASKSERVER",
        "artifact_name": "Schedule",
        "artifact_name_lower": "schedule",
    }


def get_revisions_targets():
    """
    Optional hook discovered by ophix-revisions (if installed).
    """
    return [
        {
            "name": "tasks",
            "app_label": "ophix_tasks",
            "export_command": "export_tasks",
            "encrypted": False,
            "stable": True,
        },
    ]
