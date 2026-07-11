---
sidebar_position: 2
title: Installation
---

# Installation

## uv / uvx (recommended)

Install as an isolated tool:

```bash
uv tool install bitbucket-jira-cli
```

…or run it once without installing:

```bash
uvx bitbucket-jira-cli --help
```

## pip

```bash
pip install bitbucket-jira-cli
```

## Docker

```bash
docker pull spenhouet/bitbucket-jira-cli:latest
docker run --rm spenhouet/bitbucket-jira-cli --help
```

## Verify

```bash
bj --help
bj --version
```
