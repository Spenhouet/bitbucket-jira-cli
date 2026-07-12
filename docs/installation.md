---
sidebar_position: 2
title: Installation
---

# Installation

## Recommended: one-line install (uv)

The install script sets up an isolated, self-updating CLI via
[uv](https://docs.astral.sh/uv/). No virtualenv juggling.

**macOS and Linux**

```bash
curl -LsSf uvx.sh/bitbucket-jira-cli/install.sh | sh
```

**Windows**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://uvx.sh/bitbucket-jira-cli/install.ps1 | iex"
```

Installing a specific version:

```bash
curl -LsSf uvx.sh/bitbucket-jira-cli/1.0.1/install.sh | sh
```

## Alternatives

### PyPI (pip or uv)

```bash
# Install as an isolated tool…
uv tool install bitbucket-jira-cli

# …or run it once without installing:
uvx bitbucket-jira-cli --help

# …or with pip:
pip install bitbucket-jira-cli
```

### Docker

```bash
docker pull spenhouet/bitbucket-jira-cli:latest
docker run --rm spenhouet/bitbucket-jira-cli --help
```

## Verify

```bash
bj --help
bj --version
```
