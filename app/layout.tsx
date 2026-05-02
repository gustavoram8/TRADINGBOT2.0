import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/sidebar";
import { CandlestickBackground } from "@/components/candlestick-background";

export const metadata: Metadata = {
  title: "Chuky Bot | Algorithmic Trading Platform",
  description: "ICT Strategy · MNQ",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es" suppressHydrationWarning>
      <body className="bg-bg-primary text-text-primary flex h-screen overflow-hidden">
        <CandlestickBackground />
        <Sidebar />
        <main className="flex-1 overflow-y-auto relative z-10">
          <div className="min-h-full p-6">{children}</div>
        </main>
      </body>
    </html>
  );
}
