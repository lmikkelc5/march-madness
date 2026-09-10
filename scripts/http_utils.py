import time
import requests

DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0"}
MIN_DELAY_SECONDS = 3.0

_last_request_time = 0.0


def polite_get(url, delay=MIN_DELAY_SECONDS, max_retries=5, timeout=15):
    """GET a URL while keeping at least `delay` seconds between requests
    and backing off on 429s. sports-reference.com throttles aggressively
    (~20 req/min), so every scraper should route requests through this."""
    global _last_request_time

    for attempt in range(max_retries):
        elapsed = time.monotonic() - _last_request_time
        if elapsed < delay:
            time.sleep(delay - elapsed)

        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
        _last_request_time = time.monotonic()

        if response.status_code == 429:
            wait = delay * (2 ** attempt)
            print(f"Rate limited on {url}, waiting {wait:.0f}s (attempt {attempt + 1}/{max_retries})")
            time.sleep(wait)
            continue

        response.raise_for_status()
        return response

    raise RuntimeError(f"Failed to fetch {url} after {max_retries} retries (rate limited)")
