"""Tests for `bj automation` and the Jira Automation API client."""

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from typer.testing import CliRunner

from bitbucket_jira_cli import context
from bitbucket_jira_cli._async import run
from bitbucket_jira_cli.api.automation import AutomationClient
from bitbucket_jira_cli.api.automation import automation_base
from bitbucket_jira_cli.api.automation import rule_create_payload
from bitbucket_jira_cli.commands import automation as automation_cmd
from bitbucket_jira_cli.config import Config
from bitbucket_jira_cli.errors import ApiError
from bitbucket_jira_cli.main import app

runner = CliRunner()

BASE = automation_base("c-1")

EXPORTED = {
    "rule": {
        "uuid": "0192e5ac-0e25-71de-ba7b-d972e6a2049a",
        "name": "Weekly check",
        "state": "ENABLED",
        "created": 1743568964.174,
        "updated": 1743568964.174,
        "authorAccountId": "abc",
        "ruleScopeARIs": ["ari:cloud:jira:c-1:project/10001"],
        "trigger": {
            "id": "1",
            "component": "TRIGGER",
            "type": "jira.jql.scheduled",
            "value": {"schedule": {"rRule": "FREQ=WEEKLY"}},
        },
        "components": [
            {
                "id": "2",
                "parentId": None,
                "component": "CONDITION",
                "type": "jira.condition.container.block",
                "children": [
                    {
                        "id": "3",
                        "parentId": "2",
                        "conditionParentId": "2",
                        "component": "ACTION",
                        "type": "jira.issue.create",
                        "value": {"summary": "Weekly check"},
                    }
                ],
            }
        ],
    },
    "connections": [
        {
            "id": "conn-1",
            "accountId": "abc",
            "connectionTargetKey": "key",
            "targetConfigJson": "{}",
            "authType": "OAUTH",
            "createdAt": 1.0,
            "updatedAt": 2.0,
            "container": {"id": "x", "containerType": "RULE"},
        }
    ],
}


# -- create payload ---------------------------------------------------------


def test_create_payload_drops_read_only_fields_and_ids() -> None:
    """The uuid, timestamps and every component id are removed, nested ones too."""
    payload = rule_create_payload(EXPORTED)
    rule = payload["rule"]
    assert "uuid" not in rule
    assert "created" not in rule
    assert "updated" not in rule
    assert "id" not in rule["trigger"]
    block = rule["components"][0]
    assert "id" not in block
    assert "parentId" not in block
    child = block["children"][0]
    assert {"id", "parentId", "conditionParentId"} & child.keys() == set()
    assert child["value"] == {"summary": "Weekly check"}
    assert rule["ruleScopeARIs"] == ["ari:cloud:jira:c-1:project/10001"]


def test_create_payload_is_disabled_by_default() -> None:
    """A copied rule does not start running before someone enables it."""
    assert rule_create_payload(EXPORTED)["rule"]["state"] == "DISABLED"
    assert rule_create_payload(EXPORTED, enabled=True)["rule"]["state"] == "ENABLED"


def test_create_payload_renames_and_keeps_source_intact() -> None:
    """--name replaces the name; the input dict is not modified."""
    payload = rule_create_payload(EXPORTED, name="Yearly check")
    assert payload["rule"]["name"] == "Yearly check"
    assert EXPORTED["rule"]["name"] == "Weekly check"
    assert EXPORTED["rule"]["trigger"]["id"] == "1"


def test_create_payload_keeps_only_writable_connection_fields() -> None:
    """Connection timestamps and container are read-only and dropped."""
    payload = rule_create_payload(EXPORTED)
    assert payload["connections"] == [
        {
            "id": "conn-1",
            "accountId": "abc",
            "connectionTargetKey": "key",
            "targetConfigJson": "{}",
            "authType": "OAUTH",
        }
    ]


def test_create_payload_accepts_bare_rule() -> None:
    """A file holding only the rule object works as well."""
    payload = rule_create_payload(EXPORTED["rule"])
    assert payload["rule"]["name"] == "Weekly check"
    assert "connections" not in payload


def test_create_payload_rejects_non_rule() -> None:
    """Something without a trigger is not a rule definition."""
    with pytest.raises(ValueError, match="not a rule definition"):
        rule_create_payload({"foo": "bar"})


# -- client against a mock transport ------------------------------------------


def _client(handler: Any) -> AutomationClient:
    client = AutomationClient(BASE, "Basic dummy")
    client._client = httpx.AsyncClient(base_url=BASE, transport=httpx.MockTransport(handler))
    return client


async def _call(handler: Any, method: str, *args: Any, **kwargs: Any) -> Any:
    async with _client(handler) as client:
        return await getattr(client, method)(*args, **kwargs)


def test_list_follows_cursor_pages() -> None:
    """GET /rule/summary is paged with the cursor from links.next."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if "cursor" not in request.url.params:
            return httpx.Response(
                200,
                json={"data": [{"uuid": "a"}], "links": {"next": "?cursor=NEXT&limit=100"}},
            )
        return httpx.Response(200, json={"data": [{"uuid": "b"}], "links": {"next": None}})

    rules = run(_call(handler, "list_rules"))
    assert [r["uuid"] for r in rules] == ["a", "b"]
    assert all(r.method == "GET" for r in seen)
    assert seen[0].url.path.endswith("/rest/v1/rule/summary")
    assert seen[1].url.params["cursor"] == "NEXT"


def test_list_with_filters_posts_search() -> None:
    """Filters switch to POST /rule/summary with the cursor in the body."""
    bodies: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        body = json.loads(request.content)
        bodies.append(body)
        if "cursor" not in body:
            return httpx.Response(
                200, json={"data": [{"uuid": "a"}], "links": {"next": "?cursor=C2"}}
            )
        return httpx.Response(200, json={"data": [{"uuid": "b"}], "links": {}})

    rules = run(_call(handler, "list_rules", state="DISABLED", scope="ari:x"))
    assert len(rules) == 2
    assert bodies[0] == {"state": "DISABLED", "scope": "ari:x", "limit": 100}
    assert bodies[1]["cursor"] == "C2"


def test_list_stops_at_limit() -> None:
    """The page size shrinks to the limit and no further page is fetched."""
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.params["limit"])
        data = [{"uuid": str(i)} for i in range(int(request.url.params["limit"]))]
        return httpx.Response(200, json={"data": data, "links": {"next": "?cursor=more"}})

    rules = run(_call(handler, "list_rules", limit=3))
    assert len(rules) == 3
    assert calls == ["3"]


def test_set_state_puts_value() -> None:
    """Enable and disable go through PUT /rule/{uuid}/state."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200)

    run(_call(handler, "set_state", "u-1", "DISABLED"))
    assert seen[0].method == "PUT"
    assert seen[0].url.path.endswith("/rest/v1/rule/u-1/state")
    assert json.loads(seen[0].content) == {"value": "DISABLED"}


def test_create_and_delete_requests() -> None:
    """Create posts the payload; delete hits the rule URL."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.method == "POST":
            return httpx.Response(201, json={"ruleUuid": "new"})
        return httpx.Response(200)

    created = run(_call(handler, "create_rule", {"rule": {"name": "x"}}))
    run(_call(handler, "delete_rule", "u-1"))
    assert created == {"ruleUuid": "new"}
    assert seen[0].url.path.endswith("/rest/v1/rule")
    assert json.loads(seen[0].content) == {"rule": {"name": "x"}}
    assert seen[1].method == "DELETE"
    assert seen[1].url.path.endswith("/rest/v1/rule/u-1")


def test_scope_error_explains_token_type() -> None:
    """A 401 'scope does not match' points at the token type."""

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401, json={"code": 401, "message": "Unauthorized; scope does not match"}
        )

    with pytest.raises(ApiError, match="unscoped") as info:
        run(_call(handler, "get_rule", "u-1"))
    assert info.value.status == 401


def test_error_list_and_forbidden_hint() -> None:
    """The errors array is joined, and a 403 mentions the admin requirement."""

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"errors": [{"title": "Forbidden", "detail": "No access"}]})

    with pytest.raises(ApiError, match=r"No access.*administrator"):
        run(_call(handler, "get_rule", "u-1"))


# -- cloud id resolution ----------------------------------------------------------


def test_cloud_id_from_config_or_tenant_info(monkeypatch: pytest.MonkeyPatch) -> None:
    """Gateway mode has the cloud id; site mode looks it up once per call."""
    lookups: list[str] = []

    async def fake_fetch(site: str) -> str:
        lookups.append(site)
        return "c-site"

    monkeypatch.setattr(context, "fetch_cloud_id", fake_fetch)
    gateway = Config.model_validate({"jira": {"auth_mode": "gateway", "cloud_id": "c-gw"}})
    site = Config.model_validate({"jira": {"site": "https://ex.atlassian.net"}})
    assert run(context.jira_cloud_id(gateway)) == "c-gw"
    assert run(context.jira_cloud_id(site)) == "c-site"
    assert lookups == ["https://ex.atlassian.net"]


# -- commands ------------------------------------------------------------------------


class FakeAutomation:
    """Stand-in for AutomationClient recording every call."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    async def __aenter__(self) -> "FakeAutomation":
        return self

    async def __aexit__(self, *_exc: object) -> bool:
        return False

    async def list_rules(self, **kwargs: Any) -> list[dict[str, Any]]:
        self.calls.append(("list", kwargs))
        return [
            {
                "uuid": "u-1",
                "name": "Weekly check",
                "state": "ENABLED",
                "ruleScopeARIs": ["ari:cloud:jira:c-1:project/10001"],
            }
        ]

    async def get_rule(self, uuid: str) -> dict[str, Any]:
        self.calls.append(("get", uuid))
        return EXPORTED

    async def set_state(self, uuid: str, state: str) -> None:
        self.calls.append(("state", (uuid, state)))

    async def create_rule(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("create", payload))
        return {"ruleUuid": "new-uuid"}

    async def delete_rule(self, uuid: str) -> None:
        self.calls.append(("delete", uuid))


@pytest.fixture
def fake(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FakeAutomation:
    """Point the automation commands at a fake client and an empty config dir."""
    monkeypatch.setenv("BJ_CONFIG_DIR", str(tmp_path))
    client = FakeAutomation()

    async def factory(_config: Config) -> tuple[FakeAutomation, str]:
        return client, "c-1"

    monkeypatch.setattr(automation_cmd, "automation_client", factory)
    return client


def test_group_registered() -> None:
    """The automation group shows up in the top-level help."""
    result = runner.invoke(app, ["--help"])
    assert "automation" in result.stdout


def test_list_renders_and_passes_filters(fake: FakeAutomation) -> None:
    """--state is upper-cased for the API; the rows show name, uuid and scope."""
    result = runner.invoke(app, ["automation", "list", "--state", "disabled", "--trigger", "t"])
    assert result.exit_code == 0, result.output
    assert fake.calls == [
        ("list", {"state": "DISABLED", "trigger": "t", "scope": None, "limit": 1000})
    ]
    assert "Weekly check" in result.stdout
    assert "u-1" in result.stdout
    assert "project/10001" in result.stdout


def test_list_project_id_becomes_scope_ari(fake: FakeAutomation) -> None:
    """A numeric --project is turned into a project ARI without a Jira lookup."""
    result = runner.invoke(app, ["automation", "list", "-p", "10001", "--json"])
    assert result.exit_code == 0, result.output
    assert fake.calls[0][1]["scope"] == "ari:cloud:jira:c-1:project/10001"
    assert json.loads(result.stdout)[0]["uuid"] == "u-1"


@pytest.mark.parametrize(("command", "state"), [("enable", "ENABLED"), ("disable", "DISABLED")])
def test_enable_disable(fake: FakeAutomation, command: str, state: str) -> None:
    """Enable and disable send the matching state."""
    result = runner.invoke(app, ["automation", command, "u-1"])
    assert result.exit_code == 0, result.output
    assert fake.calls == [("state", ("u-1", state))]


@pytest.mark.usefixtures("fake")
def test_view_json() -> None:
    """View --json prints the full definition."""
    result = runner.invoke(app, ["automation", "view", "u-1", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == EXPORTED


def test_export_then_import_roundtrip(fake: FakeAutomation, tmp_path: Path) -> None:
    """An exported file imports as a new, disabled rule with the new name."""
    out = tmp_path / "rule.json"
    assert runner.invoke(app, ["automation", "export", "u-1", "-o", str(out)]).exit_code == 0
    assert json.loads(out.read_text(encoding="utf-8")) == EXPORTED

    result = runner.invoke(app, ["automation", "import", str(out), "--name", "Yearly check"])
    assert result.exit_code == 0, result.output
    kind, payload = fake.calls[-1]
    assert kind == "create"
    assert payload["rule"]["name"] == "Yearly check"
    assert payload["rule"]["state"] == "DISABLED"
    assert "uuid" not in payload["rule"]


def test_import_from_stdin_enabled(fake: FakeAutomation) -> None:
    """`-` reads the definition from stdin; --enable creates it enabled."""
    result = runner.invoke(
        app, ["automation", "import", "-", "--enable", "--json"], input=json.dumps(EXPORTED)
    )
    assert result.exit_code == 0, result.output
    assert fake.calls[-1][1]["rule"]["state"] == "ENABLED"
    assert json.loads(result.stdout) == {"ruleUuid": "new-uuid"}


@pytest.mark.parametrize(("content", "message"), [("{not json", "not valid JSON"), ("[]", "rule")])
def test_import_rejects_bad_files(
    fake: FakeAutomation, tmp_path: Path, content: str, message: str
) -> None:
    """Invalid input stops before any request is sent."""
    bad = tmp_path / "bad.json"
    bad.write_text(content, encoding="utf-8")
    result = runner.invoke(app, ["automation", "import", str(bad)])
    assert result.exit_code != 0
    assert fake.calls == []
    assert message in str(result.exception) + result.output


def test_delete_with_yes(fake: FakeAutomation) -> None:
    """Delete --yes skips the prompt and deletes."""
    result = runner.invoke(app, ["automation", "delete", "u-1", "--yes"])
    assert result.exit_code == 0, result.output
    assert fake.calls == [("delete", "u-1")]
