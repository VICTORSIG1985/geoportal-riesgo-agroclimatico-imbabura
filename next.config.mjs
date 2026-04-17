/** @type {import('next').NextConfig} */
const isProd = process.env.NODE_ENV === 'production';
const repo = 'geoportal-riesgo-agroclimatico-imbabura';
const basePath = isProd ? `/${repo}` : '';

const nextConfig = {
  output: 'export',
  basePath,
  assetPrefix: isProd ? `/${repo}/` : '',
  images: { unoptimized: true },
  trailingSlash: true,
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_BASE_PATH: basePath,
  },
};

export default nextConfig;
