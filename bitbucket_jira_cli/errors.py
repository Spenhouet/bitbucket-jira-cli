"""Typed errors surfaced to the user as clean messages (no traceback)."""

from __future__ import annotations


class BjError(Exception):
    """Base class for all expected, user-facing errors."""


class ConfigError(BjError):
    """Configuration is missing or invalid."""


class AuthError(BjError):
    """Authentication is missing or rejected by a backend."""


class NotInRepoError(BjError):
    """The command needs a Bitbucket git repository but none was found."""


class BranchKeyError(BjError):
    """No Jira key could be derived from the current branch."""


class ApiError(BjError):
    """A backend returned an unexpected HTTP response."""

    def __init__(self, backend: str, status: int, message: str) -> None:
        self.backend = backend
        self.status = status
        self.message = message
        super().__init__(f"{backend} API error {status}: {message}")
