plugin_category = "module"
plugin_sort = 130

default_app_config = "ophix_tasks.apps.OphixTasksConfig"


def install_configure(conf, command):
    """configure_install hook: contribute this domain's backup target."""
    existing = conf.get("backup", "targets_extra", fallback="")
    conf.set("backup", "targets_extra", ",".join(filter(None, [existing, "tasks"])))
