import React, { type ReactNode } from "react";
import clsx from "clsx";
import Link from "@docusaurus/Link";
import useBaseUrl from "@docusaurus/useBaseUrl";
import useDocusaurusContext from "@docusaurus/useDocusaurusContext";
import Layout from "@theme/Layout";
import CodeBlock from "@theme/CodeBlock";
import Tabs from "@theme/Tabs";
import TabItem from "@theme/TabItem";
import HomepageFeatures from "@site/src/components/HomepageFeatures";
import {
  AuthenticateTabs,
  ExportTabs,
} from "@site/src/components/quickstart";
import styles from "./index.module.css";

function HomepageHeader() {
  const { siteConfig } = useDocusaurusContext();
  return (
    <header className={clsx("hero", styles.heroBanner)}>
      <div className="container">
        <img
          src={useBaseUrl("/img/banner.png")}
          alt={siteConfig.title}
          className="hero-banner"
        />
        <p className="hero__subtitle">{siteConfig.tagline}</p>
        <div className={styles.buttons}>
          <Link
            className="button button--hero button--lg"
            to="/installation"
          >
            Get started →
          </Link>
          <Link
            className="button button--hero-secondary button--lg"
            to="https://github.com/Spenhouet/bitbucket-jira-cli"
          >
            View on GitHub
          </Link>
        </div>
      </div>
    </header>
  );
}

const INSTALL_SNIPPETS = {
  unix: `# Installs an isolated, self-updating CLI via uv.
curl -LsSf uvx.sh/bitbucket-jira-cli/install.sh | sh`,
  windows: `powershell -ExecutionPolicy ByPass -c "irm https://uvx.sh/bitbucket-jira-cli/install.ps1 | iex"`,
  pip: `pip install bitbucket-jira-cli`,
  uv: `# Install as an isolated tool…
uv tool install bitbucket-jira-cli

# …or run it once without installing:
uvx bitbucket-jira-cli --help`,
  docker: `# Pull and run the prebuilt image.
docker pull spenhouet/bitbucket-jira-cli:latest
docker run --rm spenhouet/bitbucket-jira-cli --help`,
};

function InstallTabs() {
  return (
    <Tabs groupId="install-method" queryString>
      <TabItem value="linux" label="Linux">
        <CodeBlock language="bash">{INSTALL_SNIPPETS.unix}</CodeBlock>
      </TabItem>
      <TabItem value="macos" label="macOS">
        <CodeBlock language="bash">{INSTALL_SNIPPETS.unix}</CodeBlock>
      </TabItem>
      <TabItem value="windows" label="Windows">
        <CodeBlock language="powershell">{INSTALL_SNIPPETS.windows}</CodeBlock>
      </TabItem>
      <TabItem value="pip" label="pip">
        <CodeBlock language="bash">{INSTALL_SNIPPETS.pip}</CodeBlock>
      </TabItem>
      <TabItem value="uv" label="uv">
        <CodeBlock language="bash">{INSTALL_SNIPPETS.uv}</CodeBlock>
      </TabItem>
      <TabItem value="docker" label="Docker">
        <CodeBlock language="bash">{INSTALL_SNIPPETS.docker}</CodeBlock>
      </TabItem>
    </Tabs>
  );
}

function QuickstartSection() {
  return (
    <section className={styles.quickstart}>
      <div className="container">
        <div className="row">
          <div className="col col--8 col--offset-2">
            <h2 className={styles.quickstartTitle}>Get going in 60 seconds</h2>
            <p className={styles.quickstartLead}>
              Install, authenticate, ship. That's the whole flow.
            </p>

            <h3 className={styles.stepTitle}>1. Install</h3>
            <InstallTabs />

            <h3 className={styles.stepTitle}>2. Authenticate</h3>
            <AuthenticateTabs />

            <h3 className={styles.stepTitle}>3. Use it</h3>
            <ExportTabs />

            <p className={styles.quickstartFooter}>
              Detailed setup in the{" "}
              <Link to="/installation">installation docs</Link>.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

export default function Home(): ReactNode {
  const { siteConfig } = useDocusaurusContext();
  return (
    <Layout
      title={siteConfig.title}
      description={siteConfig.tagline}
    >
      <HomepageHeader />
      <main>
        <HomepageFeatures />
        <QuickstartSection />
      </main>
    </Layout>
  );
}
