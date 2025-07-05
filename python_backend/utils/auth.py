import os

import sentry_sdk
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials


def get_scraper_bearer_token() -> str:
    return os.getenv("SCRAPER_BEARER_TOKEN", "")

def get_validated_token(credentials: HTTPAuthorizationCredentials) -> None:
    expected_token = get_scraper_bearer_token()

    if credentials.scheme.lower() != "bearer" or credentials.credentials != expected_token:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "auth")
            scope.set_extra("provided_scheme", credentials.scheme)
            scope.set_extra("provided_token", credentials.credentials[:6] + "***")
            sentry_sdk.capture_message("Invalid bearer token provided", level="warning")

        raise HTTPException(status_code=401, detail="Unauthorized")


