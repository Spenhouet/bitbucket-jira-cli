---
title: CI integration
---

# CI integration

In a pipeline `bj` needs no login and no prompt. The site and email go into the config with `bj config set`, the token comes from an environment variable, and `--json` gives output a script can read.

## Setup without prompts

```bash
export BJ_PROMPT_DISABLED=1
export BJ_JIRA_TOKEN="$JIRA_API_TOKEN"            # from the CI secret store
bj config set jira.site https://example.atlassian.net
bj config set jira.email ci@example.com

bj issue list --jql 'project = DEMO AND status = "To Do"' --json
```

For Bitbucket, set `bitbucket.email` and `BJ_BITBUCKET_TOKEN` the same way. Tokens from the environment take precedence over the keyring and are never written to disk, see [Environment variables](./environment.md).

`BJ_CONFIG_DIR` points `bj` at a config folder of its own, for example a temporary folder of the job, so two jobs on one runner do not share a config.

### Scoped Jira tokens

A scoped API token works only through the `api.atlassian.com` gateway (see [Jira: two token modes](./configuration.md#jira-two-token-modes)). Set the mode and the cloud id of the site:

```bash
bj config set jira.auth_mode gateway
bj config set jira.cloud_id "$(curl -s https://example.atlassian.net/_edge/tenant_info | jq -r .cloudId)"
```

`bj auth status` checks both tokens and is a quick first step of a job.

## Docker image

Each release is published to Docker Hub for `linux/amd64` and `linux/arm64`:

```text
spenhouet/bitbucket-jira-cli:<version>
spenhouet/bitbucket-jira-cli:latest
```

The entry point is `bj`. The image runs as user `bj` (uid 1000) with the config under `/data/config` and includes `jq` for `--jq`. Pin a version in pipelines.

```bash
docker run --rm -e BJ_JIRA_TOKEN -e BJ_PROMPT_DISABLED=1 --entrypoint sh \
  spenhouet/bitbucket-jira-cli:1.11.2 -c '
    bj config set jira.site https://example.atlassian.net >/dev/null
    bj config set jira.email ci@example.com >/dev/null
    bj issue view DEMO-1 --json'
```

## GitHub Actions

```yaml
jobs:
  release-record:
    runs-on: ubuntu-latest
    env:
      BJ_PROMPT_DISABLED: "1"
      BJ_JIRA_TOKEN: ${{ secrets.JIRA_API_TOKEN }}
    steps:
      - uses: astral-sh/setup-uv@v6
      - run: uv tool install bitbucket-jira-cli
      - run: |
          bj config set jira.site https://example.atlassian.net
          bj config set jira.email ci@example.com
      - run: |
          bj issue create -p DEMO -t Task -s "Release ${{ github.ref_name }}" \
            -b "Released from ${{ github.sha }}" --json | jq -r .key
```

## GitLab CI

The entry point is cleared, so GitLab runs the job script in a shell.

```yaml
release-record:
  image:
    name: spenhouet/bitbucket-jira-cli:1.11.2
    entrypoint: [""]
  variables:
    BJ_PROMPT_DISABLED: "1"
    BJ_JIRA_TOKEN: $JIRA_API_TOKEN   # masked CI/CD variable
  script:
    - bj config set jira.site https://example.atlassian.net
    - bj config set jira.email ci@example.com
    - bj issue create -p DEMO -t Task -s "Release $CI_COMMIT_TAG" -b "Released from $CI_COMMIT_SHA"
```

## Kubernetes and Argo Workflows

An Argo Workflows step with the token from a Kubernetes Secret:

```yaml
- name: release-record
  inputs:
    parameters:
      - name: version
  script:
    image: spenhouet/bitbucket-jira-cli:1.11.2
    command: [sh]
    env:
      - name: BJ_PROMPT_DISABLED
        value: "1"
      - name: BJ_JIRA_TOKEN
        valueFrom:
          secretKeyRef:
            name: jira-token
            key: token
    source: |
      set -e
      bj config set jira.site https://example.atlassian.net
      bj config set jira.email ci@example.com
      bj issue create -p DEMO -t Task -s "Release {{inputs.parameters.version}}" -b "Released by Argo"
```

## Scripting the output

`--json` prints the raw API response, so a step can pass an issue key or a pull request id to the next one. `--jq` filters it with the `jq` binary and prints JSON, so strings keep their quotes; pipe `--json` into `jq -r` for a plain value:

```bash
key=$(bj issue create -p DEMO -t Task -s "Release 1.2.0" --json | jq -r .key)
bj issue comment "$key" -b "Deployed to staging"
```

A failed request exits with 1, a usage error with 2, see [Exit codes](./exit-codes.md) and [Output formatting](./formatting.md).
