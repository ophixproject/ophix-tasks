"""
ophix_tasks.validators
~~~~~~~~~~~~~~~~~~~~~~
Interval format validators for each supported scheduler type.

Each class exposes a static validate(interval) method that raises
django.core.exceptions.ValidationError if the interval string is not
valid for that scheduler.

Validator classes are referenced by dotted path in Scheduler.validator_class
and resolved at runtime via importlib.
"""

import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


_CRON_SHORTHANDS = frozenset([
    "@reboot", "@yearly", "@annually", "@monthly", "@weekly",
    "@daily", "@midnight", "@hourly",
])

_SYSTEMD_SHORTHANDS = frozenset([
    "annually", "daily", "hourly", "minutely", "monthly",
    "quarterly", "semi-annually", "weekly", "yearly",
])

_WTS_KEYWORDS = frozenset(["DAILY", "WEEKLY", "MONTHLY", "ONCE"])


class CronValidator:
    @staticmethod
    def validate(interval):
        # type: (str) -> None
        s = interval.strip()
        if s in _CRON_SHORTHANDS or s.lower() in _CRON_SHORTHANDS:
            return
        if len(s.split()) != 5:
            raise ValidationError(
                _("Invalid cron expression: expected 5 space-separated fields "
                  "(minute hour day-of-month month day-of-week) "
                  "or a @shorthand such as @daily or @weekly.")
            )


class SystemdValidator:
    @staticmethod
    def validate(interval):
        # type: (str) -> None
        s = interval.strip()
        if s.lower() in _SYSTEMD_SHORTHANDS:
            return
        if ":" in s:
            return  # Has a time component — assumed valid
        if re.match(r"^[\d*].*-", s):
            return  # Starts with a date pattern
        if re.match(r"^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)", s, re.IGNORECASE):
            return  # Day-of-week prefix
        raise ValidationError(
            _("Invalid systemd OnCalendar= expression. "
              "Examples: '*-*-* 02:00:00' (daily at 2am), 'daily', 'Mon *-*-* 08:00:00'. "
              "See systemd.time(7) for full syntax.")
        )


class WtsValidator:
    @staticmethod
    def validate(interval):
        # type: (str) -> None
        s = interval.strip()
        keyword = s.split()[0].upper() if s else ""
        if keyword not in _WTS_KEYWORDS:
            raise ValidationError(
                _("Invalid WTS interval. Expected: 'DAILY HH:MM', "
                  "'WEEKLY Mon HH:MM', 'MONTHLY 1 HH:MM', or 'ONCE YYYY-MM-DD HH:MM'.")
            )
