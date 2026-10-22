import { fileURLToPath } from "node:url";

import type { NextConfig } from "next";

// This folder is the app's root. Set explicitly so a lockfile in a parent folder is
// never taken for the workspace root.
const root = fileURLToPath(new URL(".", import.meta.url));

const nextConfig: NextConfig = {
  cacheComponents: true,
  // A self-contained server in .next/standalone, which the Docker image runs.
  output: "standalone",
  partialPrefetching: true,
  poweredByHeader: false,
  outputFileTracingRoot: root,
  // The case list is the home page. Redirected here rather than in a page, so the
  // redirect happens before any rendering.
  async redirects() {
    return [{ source: "/", destination: "/cases", permanent: false }];
  },
  turbopack: {
    root,
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
