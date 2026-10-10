---
title: bj api
---

# bj api

Make an authenticated request to the Bitbucket or Jira API.

## Synopsis

```
bj api [OPTIONS] PATH
```

## Description

Make an authenticated request against the Bitbucket or Jira REST API and print the JSON response. Choose the backend with `--backend`; `--field` adds parameters (query string for GET, JSON body otherwise). For a nested JSON body, pass it with `--input <file>` (`-` reads stdin), as with `gh api --input`; `--field` values then go to the query string.

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
| `--input <text>` | JSON request body from a file ('-' for stdin). Fields then go to the query. |
| `-q, --jq <text>` | Filter JSON with jq. |

## Examples

```bash
bj api /repositories/{workspace}/{repo_slug}/pullrequests
bj api --backend jira /myself
# Full REST paths from the Jira docs work too
bj api --backend jira /rest/api/3/project/PROJ
bj api --backend jira -X POST /issue/PROJ-42/comment -f body=hi
# Send a nested JSON body from a file or stdin
bj api --backend jira -X PUT /issue/PROJ-42 --input body.json
jq -c . body.json | bj api -b jira -X PUT /issue/PROJ-42 --input -
```

## See also

- [`bj`](index.md)
