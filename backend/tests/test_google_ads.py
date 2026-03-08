from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from services.google_ads import upload_conversion, is_dry_run


def test_is_dry_run_when_no_customer_id():
    with patch("services.google_ads.GOOGLE_ADS_CUSTOMER_ID", ""):
        with patch("services.google_ads.GOOGLE_ADS_DRY_RUN", False):
            assert is_dry_run() is True


def test_is_dry_run_when_flag_set():
    with patch("services.google_ads.GOOGLE_ADS_CUSTOMER_ID", "123-456-7890"):
        with patch("services.google_ads.GOOGLE_ADS_DRY_RUN", True):
            assert is_dry_run() is True


def test_is_not_dry_run_when_configured():
    with patch("services.google_ads.GOOGLE_ADS_CUSTOMER_ID", "123-456-7890"):
        with patch("services.google_ads.GOOGLE_ADS_DRY_RUN", False):
            assert is_dry_run() is False


def test_upload_conversion_dry_run():
    with patch("services.google_ads.is_dry_run", return_value=True):
        result = upload_conversion(
            gclid="test-gclid-abc",
            conversion_value=8.5,
            conversion_time=datetime(2026, 3, 8, 12, 0, 0, tzinfo=timezone.utc),
        )
    assert result["status"] == "sent (dry_run)"
    assert result["gclid"] == "test-gclid-abc"
    assert result["conversion_value"] == 8.5
    assert result["error"] is None


def test_upload_conversion_missing_gclid():
    result = upload_conversion(
        gclid="",
        conversion_value=7.0,
        conversion_time=datetime(2026, 3, 8, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert result["status"] == "failed"
    assert "gclid" in result["error"].lower()


def test_upload_conversion_missing_value():
    result = upload_conversion(
        gclid="test-gclid",
        conversion_value=None,
        conversion_time=datetime(2026, 3, 8, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert result["status"] == "failed"
    assert "value" in result["error"].lower()
