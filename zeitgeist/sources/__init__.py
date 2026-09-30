"""Signal source collectors for Zeitgeist."""

from zeitgeist.sources.base import SignalCollector
from zeitgeist.sources.github import GitHubCollector
from zeitgeist.sources.hackernews import HackerNewsCollector
from zeitgeist.sources.mock import MockCollector
from zeitgeist.sources.reddit import RedditCollector

__all__ = [
    "SignalCollector",
    "HackerNewsCollector",
    "RedditCollector",
    "GitHubCollector",
    "MockCollector",
]
