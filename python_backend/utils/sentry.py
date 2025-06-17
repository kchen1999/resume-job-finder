import os

import sentry_sdk
from dotenv import load_dotenv

# Only load .env if it exists (in development)
if os.environ.get("FLY_REGION") is None:
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

def get_sentry_dsn():
    sentry_dsn = os.environ.get("SENTRY_DSN")
    if not sentry_dsn:
        raise RuntimeError("Missing SENTRY_DSN environment variable")
    return sentry_dsn

sentry_dsn = get_sentry_dsn()

sentry_sdk.init(
    dsn=sentry_dsn,
    send_default_pii=True,
)

