import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    // Team flags/badges are the only imagery in the UI. The backend serves ESPN
    // team logos (e.g. a.espncdn.com/i/teamlogos/countries/500/can.png).
    remotePatterns: [
      {
        protocol: "https",
        hostname: "a.espncdn.com",
        pathname: "/i/teamlogos/**",
      },
    ],
  },
};

export default nextConfig;
