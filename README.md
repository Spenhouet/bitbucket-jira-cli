<p align="center">
  <a href="https://github.com/Spenhouet/bitbucket-jira-cli"><img src="https://raw.githubusercontent.com/Spenhouet/bitbucket-jira-cli/main/static/img/banner.png" style="border-radius: 15px;" alt="bitbucket-jira-cli"></a>
</p>
<p align="center">
  <em>A gh-style CLI for Bitbucket (pull requests, repos, pipelines) and Jira (issues), with branch-name-as-Jira-key automation.</em>
</p>
<p align="center">
  <a href="https://github.com/Spenhouet/bitbucket-jira-cli/actions/workflows/python-build.yml"><img src="https://github.com/Spenhouet/bitbucket-jira-cli/actions/workflows/python-build.yml/badge.svg" alt="Build Python package"></a>
  <a href="https://github.com/Spenhouet/bitbucket-jira-cli/actions/workflows/release.yml"><img src="https://github.com/Spenhouet/bitbucket-jira-cli/actions/workflows/release.yml/badge.svg" alt="Build and publish to PyPI"></a>
  <a href="https://pypi.org/project/bitbucket-jira-cli" target="_blank">
    <img src="https://img.shields.io/pypi/v/bitbucket-jira-cli?color=%2334D058&label=PyPI%20package" alt="PyPI version">
   </a>
  <a href="https://hub.docker.com/r/spenhouet/bitbucket-jira-cli" target="_blank">
    <img src="https://img.shields.io/docker/v/spenhouet/bitbucket-jira-cli?sort=semver&label=Docker%20Hub&color=2496ED&logo=docker&logoColor=white" alt="Docker Hub version">
   </a>
  <a href="https://spenhouet.github.io/bitbucket-jira-cli/" target="_blank">
    <img src="https://img.shields.io/badge/docs-online-blue" alt="Documentation">
   </a>
</p>

## What it does

`bj` brings [GitHub `gh`](https://cli.github.com/) ergonomics to Bitbucket and
Jira. It manages Bitbucket pull requests, repositories and pipelines and Jira
issues from a single noun-first command surface.

The signature feature is **branch-name-as-Jira-key**: your current git branch
carries a Jira key (e.g. `feature/PROJ-42-thing`), and commands use it to
auto-link pull requests to tickets and drive Jira transitions.

## Quickstart

### 1. Install

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
curl -LsSf uvx.sh/bitbucket-jira-cli/1.0.0/install.sh | sh
```

Alternative install methods (PyPI via `pip` / `uv`, prebuilt Docker image) are
covered in the [installation docs](https://spenhouet.github.io/bitbucket-jira-cli/installation).

### 2. Authenticate

```sh
bj auth login
```

### 3. Use it

```sh
# On a branch like feature/PROJ-42-thing:
bj pr create          # open a PR, auto-linked to PROJ-42
bj pr view            # show the PR for the current branch
bj issue view PROJ-42 # show the Jira issue
bj pipeline list      # list Bitbucket Pipelines runs
```

## Documentation

The full documentation lives at **<https://spenhouet.github.io/bitbucket-jira-cli/>**.

## Contributing

If you would like to contribute, please read [our contribution guideline](CONTRIBUTING.md).

## License

This tool is an open source project released under the [MIT License](LICENSE).
