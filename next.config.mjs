/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Disable Next.js built-in gzip compression. Without this, the compression
  // middleware buffers streaming chunks (like keepalive "\n" bytes) until the
  // gzip compressor has enough data to flush, breaking long-running API routes.
  // nginx handles compression at the proxy level when needed.
  compress: false,
  experimental: {
    instrumentationHook: true,
  },
  env: {
    PYTHON_API_URL: process.env.PYTHON_API_URL || "",
    GEMINI_API_KEY: process.env.GEMINI_API_KEY || "",
  },
};

export default nextConfig;
