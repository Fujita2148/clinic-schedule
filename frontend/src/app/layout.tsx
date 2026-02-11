import type { Metadata } from "next";
import "./globals.css";
import { AppNav } from "@/components/AppNav";

export const metadata: Metadata = {
  title: "クリニック スケジュール管理",
  description: "多層条件・自然文対応 職員シフト作成システム",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ja">
      <body className="bg-white text-gray-900 min-h-screen flex flex-col">
        <AppNav />
        {children}
      </body>
    </html>
  );
}
