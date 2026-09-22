"""Clean, cloud-only Browser Harness observation path derived from Jev Ultrafast.

No browser mutation occurs: it opens one fresh cloud browser, observes an allowlisted
public page, then stops that browser. The Jev decision role is bounded to classifying
captured text; it never emits an action or selector here.
"""
import json, os, re, time
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

from .policy import assert_allowed_url

class ObservationError(RuntimeError): pass

def _visible_identity(text, company):
    # Exact standalone visible line only; a substring in ad copy is not advertiser identity.
    expected=company.casefold().strip()
    return any(line.casefold().strip()==expected for line in (text or '').splitlines())

def _classify(text, returncode=0):
    value=(text or '').lower()
    if any(x in value for x in ('captcha','security check','temporarily blocked','log in to continue','rate limit','verify you')):
        return 'source_blocked'
    if 'no ads match your search criteria' in value: return 'no_active_ads'
    if 'library id:' in value and 'active' in value: return 'active_ads'
    return 'source_error' if returncode else 'identity_unresolved'

def observe(url, *, company, page_id, proxy_country='us', cloud_timeout=2):
    """Return visible text/IDs from a fresh cloud browser. Never falls back local."""
    assert_allowed_url(url)
    import uuid
    # BU_NAME must be set before importing Browser Harness helpers, which cache routing.
    name='jev-friend-' + uuid.uuid4().hex[:10]
    os.environ['BH_OPEN_LIVE_URL']='0'; os.environ['BU_NAME']=name
    try:
        from browser_harness.auth import auth_status
        from browser_harness.admin import start_remote_daemon, stop_remote_daemon, _browser_use
        from .vendor.browser import Browser
    except ImportError as exc:
        raise ObservationError('Install browser-harness==0.1.13 in this project environment') from exc
    if auth_status().get('status') != 'authenticated':
        raise ObservationError('Browser Use Cloud is not authenticated; run browser-harness auth login. No local fallback exists.')
    browser=None
    started=time.monotonic()
    try:
        started_remote=start_remote_daemon(name, proxyCountryCode=proxy_country, timeout=cloud_timeout, enableRecording=False)
        browser=Browser(url)
        # Browser uses CDP only. No call to act()/Agent.run() occurs.
        page=browser.observe(screenshot=False)
        text=page.get('text') or ''
        final_url=page.get('url') or ''
        ids=list(dict.fromkeys(re.findall(r'Library ID:\s*(\d+)',text)))
        final_page_id=parse_qs(urlparse(final_url).query).get('view_all_page_id',[None])[0]
        exact_identity=_visible_identity(text, company) and final_page_id == str(page_id)
        outcome=_classify(text)
        if outcome in {'active_ads','no_active_ads'} and not exact_identity: outcome='identity_unresolved'
        return {'outcome':outcome,'ads':len(ids) if outcome=='active_ads' else 0,'detail':{'visible_ad_ids':ids,
          'observed_at':datetime.now(timezone.utc).isoformat(),'elapsed_ms':round((time.monotonic()-started)*1000),
          'cloud_browser_id':started_remote.get('id'), 'browser_mode':'fresh_cloud_observe_only', 'final_url':final_url,
          'exact_requested_page_id':final_page_id == str(page_id),'exact_visible_company_line':_visible_identity(text, company),
          'evidence':'visible public page only; not an inventory or performance result'}, '_review_text':text}
    finally:
        try:
            if browser is not None: browser.close()
        finally:
            try:
                stop_remote_daemon(name)
                browser_id=locals().get('started_remote', {}).get('id')
                if browser_id:
                    readback=_browser_use('/browsers/'+str(browser_id), 'GET')
                    if readback.get('status') != 'stopped':
                        raise ObservationError('Cloud browser cleanup readback was not stopped')
            except Exception as exc:
                # Do not conceal a failed cleanup: caller receives an operational failure.
                raise ObservationError('Cloud browser cleanup could not be confirmed') from exc
