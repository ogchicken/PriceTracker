import type { NextConfig } from "next";

const isProduction = process.env.NODE_ENV === "production";

// Baseline security headers applied to every response. The CSP here only sets
// `frame-ancestors` (clickjacking protection); it deliberately does NOT restrict
// script/style/connect sources, because Clerk loads its own scripts and the root
// layout ships an inline theme script. A full content-restricting CSP (with a
// nonce and Clerk's domains enumerated) is a larger, separate change.
const securityHeaders = [
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Content-Security-Policy", value: "frame-ancestors 'none'" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
  // HSTS is only honored over HTTPS. In production Caddy terminates TLS in front
  // of Next (which itself sees plain HTTP), so gate on the build environment and
  // skip the header in local HTTP development to avoid pinning localhost.
  ...(isProduction
    ? [
        {
          key: "Strict-Transport-Security",
          value: "max-age=63072000; includeSubDomains; preload"
        }
      ]
    : [])
];

const nextConfig: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
  poweredByHeader: false,
  allowedDevOrigins: ["127.0.0.1"],
  async headers() {
    return [
      {
        source: "/:path*",
        headers: securityHeaders
      }
    ];
  },
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "m.media-amazon.com" },
      { protocol: "https", hostname: "i.ebayimg.com" }
    ]
  }
};

export default nextConfig;
