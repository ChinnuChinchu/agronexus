"""Waits until the database accepts connections, printing the reason while it does not."""

import sys
import time

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError, NoSuchModuleError

from app.core.config import settings

ATTEMPTS = 60
DELAY_SECONDS = 5

url = make_url(settings.DATABASE_URL)
print(f"[db] target: {url.drivername}://{url.host}:{url.port or 5432}/{url.database}")

for attempt in range(1, ATTEMPTS + 1):
    try:
        engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print(f"[db] connected after {attempt} attempt(s)")
        sys.exit(0)
    except (ImportError, ArgumentError, NoSuchModuleError) as exc:
        print(f"[db] configuration problem, not retrying: {type(exc).__name__}: {exc}")
        sys.exit(1)
    except Exception as exc:  # the reason is printed so it shows up in the deployment log
        reason = str(exc).splitlines()[0] if str(exc) else ""
        print(f"[db] attempt {attempt}/{ATTEMPTS} failed: {type(exc).__name__}: {reason}")
        time.sleep(DELAY_SECONDS)
    # except Exception as exc:  # the reason is printed so it shows up in the deployment log
    #     reason = str(exc).splitlines()[0] if str(exc) else ""
    #     print(f"[db] attempt {attempt}/{ATTEMPTS} failed: {type(exc).__name__}: {reason}")
    #     time.sleep(DELAY_SECONDS)

print("[db] giving up")
sys.exit(1)