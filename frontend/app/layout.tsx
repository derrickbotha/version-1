import type { Metadata } from "next";
import "./globals.css";
import { Toaster } from "react-hot-toast";

export const metadata: Metadata = {
  title: "ASA — Agentic Scholar Assistant",
  description: "AI-powered academic research and assignment platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-surface text-gray-900 min-h-screen">
        <Toaster position="top-right" />
        {children}
      </body>
    </html>
  );
}
