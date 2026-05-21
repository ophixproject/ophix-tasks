import os

from ophix.settings.utils import get_bool_env

SERVER_NAME = os.getenv("SERVER_NAME") or "taskserver"
SHOW_SCHEDULERS_MODEL = get_bool_env("SHOW_SCHEDULERS_MODEL", default=False)

# Retention period for task execution log records (used by prune_task_logs).
from ophix.settings.utils import get_int_env as _get_int_env
PRUNE_TASK_LOG_DAYS = _get_int_env("PRUNE_TASK_LOG_DAYS", default=90)
