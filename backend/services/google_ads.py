import logging
from datetime import datetime

from config import (
    GOOGLE_ADS_CUSTOMER_ID,
    GOOGLE_ADS_DRY_RUN,
    GOOGLE_ADS_CONVERSION_ACTION,
    GOOGLE_ADS_DEVELOPER_TOKEN,
    GOOGLE_ADS_CLIENT_ID,
    GOOGLE_ADS_CLIENT_SECRET,
    GOOGLE_ADS_REFRESH_TOKEN,
)

logger = logging.getLogger(__name__)


def is_dry_run() -> bool:
    """Check if we should use dry-run mode (no actual API calls)."""
    if not GOOGLE_ADS_CUSTOMER_ID:
        return True
    return GOOGLE_ADS_DRY_RUN


def upload_conversion(
    gclid: str,
    conversion_value: float | None,
    conversion_time: datetime,
) -> dict:
    """Upload an offline conversion to Google Ads.

    Returns dict with keys: status, gclid, conversion_value, error
    """
    if not gclid:
        return {
            "status": "failed",
            "gclid": gclid,
            "conversion_value": conversion_value,
            "error": "Missing GCLID — cannot upload conversion",
        }

    if conversion_value is None:
        return {
            "status": "failed",
            "gclid": gclid,
            "conversion_value": conversion_value,
            "error": "Missing conversion value — lead score not available",
        }

    if is_dry_run():
        logger.info(
            "DRY RUN: Would upload conversion gclid=%s value=%.1f action=%s customer=%s",
            gclid, conversion_value, GOOGLE_ADS_CONVERSION_ACTION, GOOGLE_ADS_CUSTOMER_ID,
        )
        return {
            "status": "sent (dry_run)",
            "gclid": gclid,
            "conversion_value": conversion_value,
            "error": None,
        }

    # Real Google Ads API upload
    try:
        _upload_to_google_ads(gclid, conversion_value, conversion_time)
        return {
            "status": "sent",
            "gclid": gclid,
            "conversion_value": conversion_value,
            "error": None,
        }
    except Exception as e:
        logger.exception("Google Ads conversion upload failed for gclid=%s", gclid)
        return {
            "status": "failed",
            "gclid": gclid,
            "conversion_value": conversion_value,
            "error": str(e),
        }


def _upload_to_google_ads(gclid: str, conversion_value: float, conversion_time: datetime):
    """Call Google Ads API to upload offline conversion.

    Requires google-ads package. Will raise ImportError if not installed.
    """
    from google.ads.googleads.client import GoogleAdsClient  # type: ignore

    credentials = {
        "developer_token": GOOGLE_ADS_DEVELOPER_TOKEN,
        "client_id": GOOGLE_ADS_CLIENT_ID,
        "client_secret": GOOGLE_ADS_CLIENT_SECRET,
        "refresh_token": GOOGLE_ADS_REFRESH_TOKEN,
        "use_proto_plus": True,
    }
    client = GoogleAdsClient.load_from_dict(credentials)
    service = client.get_service("ConversionUploadService")

    click_conversion = client.get_type("ClickConversion")
    click_conversion.gclid = gclid
    click_conversion.conversion_action = (
        f"customers/{GOOGLE_ADS_CUSTOMER_ID}/conversionActions/{GOOGLE_ADS_CONVERSION_ACTION}"
    )
    click_conversion.conversion_value = conversion_value
    click_conversion.conversion_date_time = conversion_time.strftime("%Y-%m-%d %H:%M:%S%z")
    click_conversion.currency_code = "USD"

    response = service.upload_click_conversions(
        customer_id=GOOGLE_ADS_CUSTOMER_ID.replace("-", ""),
        conversions=[click_conversion],
    )

    if response.partial_failure_error:
        raise RuntimeError(f"Partial failure: {response.partial_failure_error.message}")

    logger.info("Conversion uploaded successfully for gclid=%s", gclid)
