---
title: bj api
sidebar_label: api
---

# bj api

Make an authenticated request to the Bitbucket or Jira API.

## Synopsis

```
bj api [OPTIONS] PATH
```

## Description

Make an authenticated request against the Bitbucket or Jira REST API and print the JSON response. Choose the backend with `--backend`; `--field` adds parameters (query string for GET, JSON body otherwise).

## Arguments

| Argument | Description |
| --- | --- |
| `PATH` | API path, e.g. /repositories/{ws}/{repo}. _(required)_ |

## Options

| Option | Description |
| --- | --- |
| `-b, --backend {bitbucket|jira}` | Which API to call. _(default: bitbucket)_ |
| `-X, --method <text>` | HTTP method. _(default: GET)_ |
| `-f, --field <text>` | key=value parameter (repeatable). |
| `-q, --jq <text>` | Filter JSON with jq. |

## Examples

```bash
bj api /repositories/{workspace}/{repo_slug}/pullrequests
bj api --backend jira /myself
bj api --backend jira -X POST /issue/PROJ-42/comment -f body=hi
```

## See also

- [`bj`](index.md)
