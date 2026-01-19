import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  // 启用standalone输出模式（用于Docker）
  output: 'standalone',
};

export default nextConfig;
