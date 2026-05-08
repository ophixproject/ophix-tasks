import os

SERVER_NAME = os.getenv("SERVER_NAME") or "taskserver"
SHOW_SCHEDULERS_MODEL = os.getenv("SHOW_SCHEDULERS_MODEL", "").lower() in ("1", "true", "yes")
