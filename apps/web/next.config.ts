import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@ai-enterprises/auth"],
  output: "standalone",
  experimental: {
    serverActions: {
      bodySizeLimit: "2mb",
    },
  },
};

export default nextConfig;