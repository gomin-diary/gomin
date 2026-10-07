import type { Metadata, Viewport } from "next";
import "./globals.css";

const title = "고민일기";
const description = "당신의 이야기를 천천히 만나보는 고민일기";
const deploymentHost = process.env.VERCEL_PROJECT_PRODUCTION_URL || process.env.VERCEL_URL;
const siteUrl = process.env.NEXT_PUBLIC_SITE_URL
  || (deploymentHost ? `https://${deploymentHost}` : "http://localhost:3000");
const socialImage = {
  url: "/images/og/gomin-diary.png",
  width: 1200,
  height: 630,
  alt: "새싹을 머리에 얹은 고민일기 캐릭터와 고민일기 제목",
};

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title,
  description,
  icons: {
    icon: { url: "/images/icons/sprout.svg", type: "image/svg+xml", sizes: "any" },
  },
  openGraph: {
    type: "website",
    locale: "ko_KR",
    siteName: title,
    title,
    description,
    images: [socialImage],
  },
  twitter: {
    card: "summary_large_image",
    title,
    description,
    images: [socialImage],
  },
};

export const viewport: Viewport = { width: "device-width", initialScale: 1, viewportFit: "cover" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
