import React, { type ReactNode } from "react";
import clsx from "clsx";
import Link from "@docusaurus/Link";
import styles from "./styles.module.css";

type Feature = {
  icon: string;
  title: string;
  description: ReactNode;
  href: string;
};

const FEATURES: Feature[] = [
  {
    icon: "🚀",
    title: "One-command install",
    href: "/installation",
    description: (
      <>
        A single <code>uv</code> command installs an isolated, self-updating
        CLI. No virtualenv juggling.
      </>
    ),
  },
  {
    icon: "🔀",
    title: "gh-style pull requests",
    href: "/usage",
    description: (
      <>
        Create, view, review and merge Bitbucket pull requests with the same
        noun-first ergonomics you know from <code>gh</code>.
      </>
    ),
  },
  {
    icon: "🎫",
    title: "Jira issues",
    href: "/usage",
    description: (
      <>
        Search (JQL), view, create, comment on and transition Jira issues
        without leaving the terminal.
      </>
    ),
  },
  {
    icon: "🌿",
    title: "Branch-key automation",
    href: "/usage",
    description: (
      <>
        Your branch name carries the Jira key. <code>bj</code> auto-links PRs to
        tickets and transitions them on create and merge.
      </>
    ),
  },
  {
    icon: "⚙️",
    title: "Pipelines",
    href: "/usage",
    description: (
      <>
        Trigger, list and stream logs for Bitbucket Pipelines — the{" "}
        <code>gh run</code> analog.
      </>
    ),
  },
  {
    icon: "🔐",
    title: "Cloud & Server",
    href: "/installation",
    description: (
      <>
        Works against Bitbucket Cloud and Jira Cloud, with scoped API tokens for
        each backend kept separate.
      </>
    ),
  },
];

function FeatureCard({ icon, title, description, href }: Feature) {
  return (
    <Link to={href} className={clsx("col col--4", styles.featureCol)}>
      <div className={clsx("feature-card", styles.featureCard)}>
        <span className="feature-icon" aria-hidden="true">
          {icon}
        </span>
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
    </Link>
  );
}

export default function HomepageFeatures(): ReactNode {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FEATURES.map((f) => (
            <FeatureCard key={f.title} {...f} />
          ))}
        </div>
      </div>
    </section>
  );
}
