"""Lufthansa Group careers scraper (apply.lufthansagroup.careers).

www.lufthansagroup.careers is an Angular shell with no server-rendered links -
the actual board lives on the ``apply.`` subdomain, a server-rendered PHP site
that publishes a sitemap and embeds JSON-LD JobPosting on every job page, so
``PhenomScraper`` handles it once pointed at the right host.

Its job URLs are ``index.php?ac=jobad&id=133022`` - no title anywhere in the
URL - so the slug pre-filter cannot work and every posting has to be fetched
and filtered on its JSON-LD title. That is ~300 requests, hence the throttle.
"""

from .phenom import PhenomScraper


class LufthansaScraper(PhenomScraper):
    """Lufthansa Group - sitemap + JSON-LD, opaque job URLs."""

    prefilter_by_slug = False

    def __init__(self, **kwargs):
        kwargs.setdefault("company_name", "Lufthansa Group")
        kwargs.setdefault("host", "apply.lufthansagroup.careers")
        kwargs.setdefault("domain", "lufthansagroup.com")
        kwargs.setdefault("job_url_match", "ac=jobad")
        kwargs.setdefault("request_delay", 0.2)
        super().__init__(**kwargs)
