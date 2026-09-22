"""Executable Browser Use + Jev collection adapter.

The included minimal Browser Harness observer is derived from the MIT-licensed
`browser-use/jev-ultrafast` project (see vendor/LICENSE-JEV-ULTRAFAST.txt). It runs
fresh Browser Use Cloud browsers only and performs no browser actions. Jev's bounded
review is intentionally not used to drive a browser action in this observe-only flow.
"""
from .policy import assert_allowed_url
from .cloud_observer import observe

def collect(job, *, timeout=180):
    """Execute one cloud-isolated observation; timeout is documented upstream lifecycle only."""
    url=assert_allowed_url(job['url'])
    return observe(url, company=job['company']['name'], page_id=job['company']['page_id'])
