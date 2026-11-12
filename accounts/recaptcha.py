import json
import logging
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings


logger = logging.getLogger(__name__)
VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"


def verify_recaptcha(response_token, remote_ip=None):
    if not settings.RECAPTCHA_SITE_KEY or not settings.RECAPTCHA_SECRET_KEY:
        logger.error("Login CAPTCHA rejected because reCAPTCHA keys are not configured.")
        return False
    if not response_token:
        return False

    payload = {
        "secret": settings.RECAPTCHA_SECRET_KEY,
        "response": response_token,
    }
    if remote_ip:
        payload["remoteip"] = remote_ip

    request = Request(
        VERIFY_URL,
        data=urlencode(payload).encode("ascii"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=5) as response:
            result = json.loads(response.read(65536))
    except (URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError):
        logger.warning("Login CAPTCHA verification service could not be reached.", exc_info=True)
        return False

    if not isinstance(result, dict):
        logger.warning("Login CAPTCHA verification service returned an invalid response.")
        return False
    return result.get("success") is True
