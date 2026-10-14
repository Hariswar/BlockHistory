import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Source crops come straight from the Library of Congress image server.
  images: { unoptimized: true },
};

export default nextConfig;
