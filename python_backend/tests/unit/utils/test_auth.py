from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from utils.auth import get_validated_token
from utils.constants import HTTP_STATUS_UNAUTHORIZED


@pytest.mark.parametrize(
    ("provided_scheme", "provided_token"),
    [
        ("Basic", "wrongtoken"),
        ("Bearer", "wrongtoken"),
        ("basic", "supersecrettoken"),
        ("Bearer", ""),
    ]
)
@patch("utils.auth.sentry_sdk.capture_message")
def test_invalid_token_triggers_sentry_and_raises(
    mock_capture_message: MagicMock,
    provided_scheme: str,
    provided_token : str,
) -> None:
    creds = HTTPAuthorizationCredentials(scheme=provided_scheme, credentials=provided_token)

    with patch("utils.auth.get_scraper_bearer_token", return_value="supersecrettoken"), \
    pytest.raises(HTTPException) as exc_info:
        get_validated_token(creds)

    assert exc_info.value.status_code == HTTP_STATUS_UNAUTHORIZED
    assert "Unauthorized" in str(exc_info.value.detail)

    mock_capture_message.assert_called_once_with("Invalid bearer token provided", level="warning")


@patch("utils.auth.get_scraper_bearer_token", return_value="supersecrettoken")
def test_valid_token_passes(get_token_mock: MagicMock) -> None:
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="supersecrettoken")

    get_validated_token(creds)
    get_token_mock.assert_called_once()
