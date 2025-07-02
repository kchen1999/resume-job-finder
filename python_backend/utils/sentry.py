import os
from pathlib import Path

import sentry_sdk
from dotenv import load_dotenv

if os.environ.get("FLY_REGION") is None:
    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)

def get_sentry_dsn() -> str:
    sentry_dsn = os.environ.get("SENTRY_DSN")
    if not sentry_dsn:
        error_msg = "Missing SENTRY_DSN environment variable"
        raise RuntimeError(error_msg)
    return sentry_dsn

sentry_dsn = get_sentry_dsn()

sentry_sdk.init(
    dsn=sentry_dsn,
    send_default_pii=True,
)

