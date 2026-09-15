import time
import requests

DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0"}
MIN_DELAY_SECONDS = 3.0
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

_last_request_time = 0.0


def polite_get(url, delay=MIN_DELAY_SECONDS, max_retries=5, timeout=15):
    """GET a URL while keeping at least `delay` seconds between requests
    and backing off on rate limiting (429) or transient server/gateway
    errors (5xx) and connection issues. sports-reference.com throttles
    aggressively (~20 req/min) and occasionally times out under load, so
    every scraper should route requests through this rather than failing
    a whole multi-hour backfill over one flaky request."""
    global _last_request_time

    for attempt in range(max_retries):
        elapsed = time.monotonic() - _last_request_time
        if elapsed < delay:
            time.sleep(delay - elapsed)

        try:
            response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
        except requests.exceptions.RequestException as exc:
            _last_request_time = time.monotonic()
            wait = delay * (2 ** attempt)
            print(f"Request error on {url} ({exc}), waiting {wait:.0f}s (attempt {attempt + 1}/{max_retries})")
            time.sleep(wait)
            continue

        _last_request_time = time.monotonic()

        if response.status_code in RETRYABLE_STATUS_CODES:
            wait = delay * (2 ** attempt)
            print(f"{response.status_code} on {url}, waiting {wait:.0f}s (attempt {attempt + 1}/{max_retries})")
            time.sleep(wait)
            continue

        response.raise_for_status()
        return response

    raise RuntimeError(f"Failed to fetch {url} after {max_retries} retries")
