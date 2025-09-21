from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta

# Default to UTC-5 unless you pass a different tz
TZ_MINUS_5 = timezone(timedelta(hours=-5))

def human_delta_to_now(dt_utc: datetime, tz: timezone = TZ_MINUS_5) -> str:
    """
    Format the delta between now and dt_utc in the following priority:
      - >= 1 year:     "3Y 2M"
      - >= 1 month:    "2M 5D"
      - < 1 month:
          - >= 3 days: "5D 18H"
          - >= 1 day:  "1D 18H30"
          - >= 1 hour: "18H 30M"
          - < 1 hour:  "0H 30M"
    """

    # Normalize to target timezone
    dt_local = dt_utc.astimezone(tz)
    now_local = datetime.now(tz)

    # If it's in the future, flip so we still show a positive duration
    future = dt_local > now_local
    if future:
        dt_local, now_local = now_local, dt_local

    delta = relativedelta(now_local, dt_local)

    # Years / Months path
    if delta.years > 0:
        return f"{delta.years}Y {delta.months}M"
    if delta.months > 0:
        return f"{delta.months}M {delta.days}D"

    # Sub-month path
    d, h, m = delta.days, delta.hours, delta.minutes

    if d >= 3:
        return f"{d}D {h}H"
    if d >= 1:
        return f"{d}D {h}H{m:02d}"
    if h >= 1:
        return f"{h}H {m}M"

    # Less than 1 hour
    return f"0H {m}M"

def human_delta_2_times(dt_1: datetime, dt_2: datetime) -> str:
    """
    Format the delta between two datetimes in the following priority:
      - >= 1 year:     "3Y 2M"
      - >= 1 month:    "2M 5D"
      - < 1 month:
          - >= 3 days: "5D 18H"
          - >= 1 day:  "1D 18H30"
          - >= 1 hour: "18H 30M"
          - < 1 hour:  "0H 30M"
    """

    # Ensure positive delta
    if dt_1 > dt_2:
        dt_1, dt_2 = dt_2, dt_1

    delta = relativedelta(dt_2, dt_1)

    # Years / Months path
    if delta.years > 0:
        return f"{delta.years}Y {delta.months}M"
    if delta.months > 0:
        return f"{delta.months}M {delta.days}D"

    # Sub-month path
    d, h, m = delta.days, delta.hours, delta.minutes

    if d >= 3:
        return f"{d}D {h}H"
    if d >= 1:
        return f"{d}D {h}H{m:02d}"
    if h >= 1:
        return f"{h}H {m}M"

    # Less than 1 hour
    return f"0H {m}M"

def timezone_to_monthddyyyy_hhmm(dt_utc: datetime, tz:timezone = TZ_MINUS_5) -> str:
    if dt_utc is not None:
        # Normalize to target timezone
        dt_local = dt_utc.astimezone(tz)
        return f"{dt_local.strftime("%B")} {dt_local.day}, {dt_local.year} ({dt_local.hour}:{dt_local.minute})"
    else:
        return None

def timezone_to_ddmonthyyyy_hhmm(dt_utc: datetime, tz:timezone = TZ_MINUS_5) -> str:
    if dt_utc is not None:
        # Normalize to target timezone
        dt_local = dt_utc.astimezone(tz)
        return f"{dt_local.day}-{dt_local.strftime("%B")}-{dt_local.year} ({dt_local.hour}:{dt_local.minute})"
    else:
        return None