/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  transpilePackages: ["@rdc/domain", "@rdc/client", "@rdc/ui"],
};

export default nextConfig;
