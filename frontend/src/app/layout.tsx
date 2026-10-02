import type { Metadata, Viewport } from "next";
import { UiStoreProvider } from "@/providers/ui-store-provider";
import { AuthProvider } from "@/providers/auth-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: "고민일기",
  description: "당신의 이야기를 천천히 만나보는 고민일기",
};

export const viewport: Viewport = { width: "device-width", initialScale: 1, viewportFit: "cover" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <body><UiStoreProvider><AuthProvider>{children}</AuthProvider></UiStoreProvider></body>
    </html>
  );
}
