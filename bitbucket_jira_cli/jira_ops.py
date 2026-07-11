"""Higher-level Jira operations built on the client (transitions, linking)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bitbucket_jira_cli.api.jira import JiraClient


async def find_transition_id(client: JiraClient, key: str, target_name: str) -> str | None:
    """Resolve a transition name (case-insensitive) to its workflow id."""
    transitions = await client.get_transitions(key)
    target = target_name.strip().lower()
    for transition in transitions:
        if str(transition.get("name", "")).strip().lower() == target:
            return str(transition["id"])
    # Also match the destination status name (e.g. "Done" as a status).
    for transition in transitions:
        to_name = transition.get("to", {}).get("name", "")
        if str(to_name).strip().lower() == target:
            return str(transition["id"])
    return None


async def transition_to(client: JiraClient, key: str, target_name: str) -> bool:
    """Transition an issue to a named state. Returns False if unavailable."""
    transition_id = await find_transition_id(client, key, target_name)
    if transition_id is None:
        return False
    await client.transition_issue(key, transition_id)
    return True


async def link_pr(client: JiraClient, key: str, pr_url: str, title: str) -> None:
    """Attach a PR URL to an issue as a remote link (idempotent via globalId)."""
    await client.create_remote_link(key, pr_url, title, global_id=pr_url)
