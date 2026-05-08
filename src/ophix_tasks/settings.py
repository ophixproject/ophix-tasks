import os

from ophix.settings.utils import get_bool_env

SERVER_NAME = os.getenv("SERVER_NAME") or "taskserver"
SHOW_SCHEDULERS_MODEL = get_bool_env("SHOW_SCHEDULERS_MODEL", default=False)
