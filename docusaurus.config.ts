import { themes as prismThemes } from "prism-react-renderer";
import type { Config } from "@docusaurus/types";
import type * as Preset from "@docusaurus/preset-classic";

const baseUrl = "/bitbucket-jira-cli/";

const config: Config = {
  title: "Bitbucket Jira CLI",
  tagline:
    "A gh-style CLI for Bitbucket pull requests, repos and pipelines, and Jira issues — with branch-name-as-Jira-key automation.",
  favicon: "img/favicon.svg",

  // Full favicon set (generated with the banner). Docusaurus prefixes `favicon`
  // with baseUrl automatically; headTags hrefs are literal, so build them from
  // the same baseUrl constant to stay in sync.
  headTags: [
    {
      tagName: "link",
      attributes: {
        rel: "apple-touch-icon",
        sizes: "180x180",
        href: `${baseUrl}img/apple-touch-icon.png`,
      },
    },
    {
      tagName: "link",
      attributes: {
        rel: "icon",
        type: "image/png",
        sizes: "32x32",
        href: `${baseUrl}img/favicon-32x32.png`,
      },
    },
    {
      tagName: "link",
      attributes: {
        rel: "icon",
        type: "image/png",
        sizes: "16x16",
        href: `${baseUrl}img/favicon-16x16.png`,
      },
    },
    {
      tagName: "link",
      attributes: {
        rel: "manifest",
        href: `${baseUrl}img/site.webmanifest`,
      },
    },
  ],

  url: "https://spenhouet.github.io",
  baseUrl,

  organizationName: "Spenhouet",
  projectName: "bitbucket-jira-cli",
  trailingSlash: false,

  onBrokenLinks: "throw",

  i18n: {
    defaultLocale: "en",
    locales: ["en"],
  },

  presets: [
    [
      "classic",
      {
        docs: {
          sidebarPath: "./sidebars.ts",
          routeBasePath: "/",
          // Internal design docs use API notation ({workspace}, <KEY>) that
          // Docusaurus would try to parse as MDX/JSX. They live in the repo for
          // reference but are not part of the published site.
          exclude: ["research/**"],
          editUrl: "https://github.com/Spenhouet/bitbucket-jira-cli/edit/main/",
          showLastUpdateAuthor: true,
          showLastUpdateTime: true,
          // Versioning is driven by git tags via scripts/build-versions.mjs.
          // The script writes versioned_docs/, versioned_sidebars/, versions.json
          // at build time and exports DOCS_LAST_VERSION pointing at the newest tag.
          lastVersion: process.env.DOCS_LAST_VERSION || "current",
          versions: {
            current: {
              label: process.env.DOCS_LAST_VERSION ? "Next 🚧" : "Current",
              path: process.env.DOCS_LAST_VERSION ? "next" : "",
              banner: process.env.DOCS_LAST_VERSION ? "unreleased" : "none",
            },
          },
        },
        blog: false,
        theme: {
          customCss: "./src/css/custom.css",
        },
        sitemap: {
          changefreq: "weekly",
          priority: 0.5,
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    image: "img/banner.png",
    colorMode: {
      defaultMode: "dark",
      respectPrefersColorScheme: true,
    },
    announcementBar: {
      id: "github_star",
      content:
        '⭐ If you like <strong>bitbucket-jira-cli</strong>, star it on <a target="_blank" rel="noopener noreferrer" href="https://github.com/Spenhouet/bitbucket-jira-cli">GitHub</a>!',
      backgroundColor: "var(--ifm-color-primary-darker)",
      textColor: "#ffffff",
      isCloseable: true,
    },
    navbar: {
      title: "Bitbucket Jira CLI",
      logo: {
        alt: "bitbucket-jira-cli logo",
        src: "img/favicon.svg",
      },
      items: [
        {
          type: "docSidebar",
          sidebarId: "docsSidebar",
          position: "left",
          label: "Docs",
        },
        {
          type: "docsVersionDropdown",
          position: "right",
          dropdownActiveClassDisabled: true,
        },
        {
          href: "https://pypi.org/project/bitbucket-jira-cli/",
          label: "PyPI",
          position: "right",
        },
        {
          href: "https://github.com/Spenhouet/bitbucket-jira-cli",
          position: "right",
          className: "header-github-link",
          "aria-label": "GitHub repository",
        },
      ],
    },
    footer: {
      style: "dark",
      links: [
        {
          title: "Docs",
          items: [
            { label: "Introduction", to: "/" },
            { label: "Installation", to: "/installation" },
            { label: "Usage", to: "/usage" },
          ],
        },
        {
          title: "Community",
          items: [
            {
              label: "Issues",
              href: "https://github.com/Spenhouet/bitbucket-jira-cli/issues",
            },
            {
              label: "Discussions",
              href: "https://github.com/Spenhouet/bitbucket-jira-cli/discussions",
            },
          ],
        },
        {
          title: "More",
          items: [
            { label: "Contributing", to: "/contributing" },
            {
              label: "GitHub",
              href: "https://github.com/Spenhouet/bitbucket-jira-cli",
            },
            {
              label: "PyPI",
              href: "https://pypi.org/project/bitbucket-jira-cli/",
            },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} Sebastian Penhouet. Built with Docusaurus.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: [
        "bash",
        "powershell",
        "yaml",
        "json",
        "toml",
        "diff",
      ],
    },
    docs: {
      sidebar: {
        hideable: true,
        autoCollapseCategories: false,
      },
    },
    tableOfContents: {
      minHeadingLevel: 2,
      maxHeadingLevel: 4,
    },
  } satisfies Preset.ThemeConfig,

  plugins: [
    [
      require.resolve("@easyops-cn/docusaurus-search-local"),
      {
        hashed: true,
        indexBlog: false,
        docsRouteBasePath: "/",
        highlightSearchTermsOnTargetPage: true,
        explicitSearchResultPath: true,
      },
    ],
  ],

  markdown: {
    // Treat .md as CommonMark (not MDX) so the generated command reference can
    // contain API notation like {workspace} and <KEY> literally. .mdx stays MDX.
    format: "detect",
    mermaid: false,
    hooks: {
      onBrokenMarkdownLinks: "warn",
    },
  },
};

export default config;
