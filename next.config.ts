import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  experimental: {
    serverActions: {
      allowedOrigins: ["localhost:3000"],
    },
  },
  env: {
    PYTHON_API_URL: process.env.PYTHON_API_URL || "",
    GEMINI_API_KEY: process.env.GEMINI_API_KEY || "",
  },
};

export default nextConfig;
