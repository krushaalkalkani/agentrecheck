import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The dashboard is fully dynamic and per-user, so it uses the classic
  // request-time rendering model rather than Cache Components.
  cacheComponents: false,
  // Native/WASM database drivers must not be bundled.
  serverExternalPackages: ["@electric-sql/pglite", "postgres"],
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
