import type { SidebarsConfig } from "@docusaurus/plugin-content-docs";

const sidebars: SidebarsConfig = {
  docsSidebar: [
    "intro",
    {
      type: "category",
      label: "Quickstart",
      collapsed: false,
      items: ["installation", "usage"],
    },
    "contributing",
  ],
};

export default sidebars;
