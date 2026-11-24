"""Print the ISO publish time: today at PUBLISH_HOUR (Vietnam time), or now + 20 min if that has passed."""
import os
from datetime import datetime, timedelta, timezone

VN = timezone(timedelta(hours=7))
hour = int(os.environ.get("PUBLISH_HOUR", "18"))
now = datetime.now(VN)
target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
if target - now < timedelta(minutes=20):
    target = (now + timedelta(minutes=20)).replace(second=0, microsecond=0)
print(target.isoformat())
