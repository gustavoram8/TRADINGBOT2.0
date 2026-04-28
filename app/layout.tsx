import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/sidebar";

export const metadata: Metadata = {
  title: "Chuky Bot | Algorithmic Trading Platform",
  description: "ICT Strategy · MNQ · OneUpTrader $50k",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es" suppressHydrationWarning>
      <body className="bg-bg-primary text-text-primary flex h-screen overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto">
          <div className="min-h-full p-6">{children}</div>
        </main>
      </body>
    </html>
  );
}
