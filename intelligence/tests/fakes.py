"""Test doubles for the outside world: Gemini and websites. No network, fully scripted."""

import json

from intelligence.services.ai_client import Reply
from intelligence.services.url_fetcher import FetchBlocked, FetchFailed, Page


class FakeTransport:
    """Plays back a script of Gemini replies (or exceptions), one per call."""

    def __init__(self, *script):
        self.script = list(script)
        self.requests = []

    def generate(self, **request):
        self.requests.append(request)
        step = self.script.pop(0)
        if isinstance(step, Exception):
            raise step
        return step


def reply(data: dict, sources=()) -> Reply:
    return Reply(text=json.dumps(data), sources=list(sources))


class FakeFetcher:
    """
    A pretend website: {url: html}. URLs in `disallowed` are refused by "robots.txt";
    URLs missing from `pages` fail like a 404.
    """

    def __init__(self, pages: dict[str, str], disallowed=(), blocked_site=None):
        self.pages = pages
        self.disallowed = set(disallowed)
        self.blocked_site = blocked_site
        self.fetched = []

    def allowed(self, url):
        if self.blocked_site:
            raise FetchBlocked(self.blocked_site)
        return url not in self.disallowed

    def fetch(self, url):
        if url in self.disallowed:
            raise FetchBlocked(f"robots.txt asks bots not to read {url}.")
        if url not in self.pages:
            raise FetchFailed(f"{url} answered 404.")
        self.fetched.append(url)
        return Page(url, url, 200, self.pages[url])
