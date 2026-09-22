"""Non-negotiable browser collection policy."""
from urllib.parse import urlparse

INSTAGRAM = "instagram.com"
META_LIBRARY_HOSTS = {"facebook.com", "www.facebook.com"}

class PolicyError(ValueError):
    pass

def is_domain(host: str, domain: str) -> bool:
    return host == domain or host.endswith("." + domain)

def meta_library_url(page_id: str) -> str:
    if not str(page_id).isdigit():
        raise PolicyError("page_id must be decimal digits")
    return ("https://www.facebook.com/ads/library/?active_status=active&ad_type=all"
            "&country=US&media_type=all&search_type=page&view_all_page_id=" + str(page_id))

def assert_allowed_url(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme != "https" or not host:
        raise PolicyError("only HTTPS URLs are allowed")
    if is_domain(host, INSTAGRAM):
        raise PolicyError("Instagram browser or UI automation is prohibited")
    if host not in META_LIBRARY_HOSTS or not parsed.path.startswith("/ads/library"):
        raise PolicyError("only public facebook.com/ads/library URLs are permitted")
    return url
