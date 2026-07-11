"""bitbucket-jira-cli: a gh-style CLI for Bitbucket and Jira."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version

try:
    __version__ = version("bitbucket-jira-cli")
except PackageNotFoundError:  # pragma: no cover - not installed (e.g. running from source)
    __version__ = "0.0.0"
