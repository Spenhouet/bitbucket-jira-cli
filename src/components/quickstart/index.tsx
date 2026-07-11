import React, { type ReactNode } from "react";
import Tabs from "@theme/Tabs";
import TabItem from "@theme/TabItem";
import CodeBlock from "@theme/CodeBlock";
import Link from "@docusaurus/Link";

/**
 * Build a tab group keyed by the install-method groupId, so it stays in sync
 * with the install tabs on the landing / installation pages.
 *
 * The non-docker tabs share the same `local` content; the docker tab shows the
 * container equivalent.
 */
function makeStepTabs(local: ReactNode, docker: ReactNode) {
  return (
    <Tabs groupId="install-method" queryString>
      <TabItem value="uv" label="uv">
        {local}
      </TabItem>
      <TabItem value="pip" label="pip">
        {local}
      </TabItem>
      <TabItem value="docker" label="Docker">
        {docker}
      </TabItem>
    </Tabs>
  );
}

/** Step 2: Authenticate against Bitbucket and Jira. */
export function AuthenticateTabs() {
  return makeStepTabs(
    <CodeBlock language="bash">{`bj auth login`}</CodeBlock>,
    <>
      <p>
        The container has no interactive prompt. Pass credentials via{" "}
        <code>BJ_*</code> environment variables or mount a config file:
      </p>
      <CodeBlock language="bash">
        {`docker run --rm \\
  -e BJ_BITBUCKET__TOKEN \\
  -e BJ_JIRA__TOKEN \\
  spenhouet/bitbucket-jira-cli auth status`}
      </CodeBlock>
    </>,
  );
}

/** Step 3: Use it. `bj pr create` locally, `docker run … ` for Docker. */
export function ExportTabs() {
  return makeStepTabs(
    <CodeBlock language="bash">
      {`# On a branch like feature/PROJ-42-thing, open a PR linked to PROJ-42:
bj pr create
bj pr view
bj issue view PROJ-42`}
    </CodeBlock>,
    <CodeBlock language="bash">
      {`docker run --rm \\
  -v "$PWD:/data" \\
  spenhouet/bitbucket-jira-cli pr view`}
    </CodeBlock>,
  );
}

/** "Verify the install" tab variants for the installation page. */
export function VerifyTabs() {
  return makeStepTabs(
    <CodeBlock language="bash">{`bj --help`}</CodeBlock>,
    <CodeBlock language="bash">
      {`docker run --rm spenhouet/bitbucket-jira-cli --help`}
    </CodeBlock>,
  );
}
