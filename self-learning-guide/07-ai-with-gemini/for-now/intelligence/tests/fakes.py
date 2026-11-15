"""Test doubles for the outside world: Gemini and websites. No network, fully scripted."""

import json

from intelligence.services.ai_client import Reply


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
