import type { Metadata } from "next";
import { UiStoreProvider } from "@/providers/ui-store-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: "Gomin",
  description: "Gomin 웹 애플리케이션",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <body><UiStoreProvider>{children}</UiStoreProvider></body>
    </html>
  );
}
