import type { NextConfig } from "next";

// The Python FastAPI server (`mrds-api` / `python -m mrds.api`) is the data plane.
// Browser requests hit `/api/*` same-origin and are proxied here, so the client never
// needs CORS and the backend origin stays configurable for deploys.
const API_ORIGIN = process.env.MRDS_API_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_ORIGIN}/api/:path*` }];
  },
};

export default nextConfig;
