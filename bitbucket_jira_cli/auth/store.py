"""Token storage, mirroring gh: env override, then OS keyring, then a file.

Read precedence:  ``BJ_<BACKEND>_TOKEN`` env  →  OS keyring  →  ``credentials.yml``.
Write: keyring by default; ``credentials.yml`` (0600) when ``insecure=True``.
The env override is never persisted.
"""

from __future__ import annotations

import base64
import contextlib
import os
from typing import Literal

import keyring
import yaml
from keyring.errors import KeyringError

from bitbucket_jira_cli.config import credentials_path

KEYRING_SERVICE = "bitbucket-jira-cli"
Backend = Literal["bitbucket", "jira"]
BACKENDS: tuple[Backend, ...] = ("bitbucket", "jira")


def _env_var(backend: Backend) -> str:
    return f"BJ_{backend.upper()}_TOKEN"


def _read_credentials_file() -> dict[str, str]:
    path = credentials_path()
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _write_credentials_file(data: dict[str, str]) -> None:
    path = credentials_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    path.write_text(yaml.safe_dump(data, sort_keys=True), encoding="utf-8")
    path.chmod(0o600)


def get_token(backend: Backend) -> str | None:
    """Resolve a token via env → keyring → credentials file."""
    if env := os.environ.get(_env_var(backend)):
        return env
    try:
        if token := keyring.get_password(KEYRING_SERVICE, backend):
            return token
    except KeyringError:
        pass
    return _read_credentials_file().get(backend)


def token_source(backend: Backend) -> str | None:
    """Where the active token comes from, for `bj auth status` (or None)."""
    if os.environ.get(_env_var(backend)):
        return f"env ({_env_var(backend)})"
    try:
        if keyring.get_password(KEYRING_SERVICE, backend):
            return "keyring"
    except KeyringError:
        pass
    if backend in _read_credentials_file():
        return f"file ({credentials_path()})"
    return None


def set_token(backend: Backend, token: str, *, insecure: bool = False) -> str:
    """Persist a token. Returns where it was stored ('keyring' or 'file')."""
    if not insecure:
        try:
            keyring.set_password(KEYRING_SERVICE, backend, token)
        except KeyringError:
            insecure = True  # no usable backend; fall back to the file
        else:
            return "keyring"
    data = _read_credentials_file()
    data[backend] = token
    _write_credentials_file(data)
    return "file"


def delete_token(backend: Backend) -> None:
    with contextlib.suppress(KeyringError):
        keyring.delete_password(KEYRING_SERVICE, backend)
    data = _read_credentials_file()
    if backend in data:
        del data[backend]
        _write_credentials_file(data)


def basic_header(email: str, token: str) -> str:
    raw = f"{email}:{token}".encode()
    return "Basic " + base64.b64encode(raw).decode("ascii")
