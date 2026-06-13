import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    // Team flags/badges are the only imagery in the UI (dashboard.md §8).
    // flagcdn.com backs the mock dataset; a.espncdn.com backs the live backend
    // (ESPN team logos, e.g. /i/teamlogos/countries/500/can.png).
    remotePatterns: [
      {
        protocol: "https",
        hostname: "flagcdn.com",
      },
      {
        protocol: "https",
        hostname: "a.espncdn.com",
        pathname: "/i/teamlogos/**",
      },
    ],
  },
};

export default nextConfig;
