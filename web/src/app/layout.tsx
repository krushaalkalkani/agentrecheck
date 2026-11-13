import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: { default: "AgentRecheck — CI/CD for AI agents", template: "%s · AgentRecheck" },
  description:
    "Catch regressions in tool-using AI agents before they ship. Record runs, snapshot them into tests, and replay them in CI.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    // Dark mode by default.
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} dark h-full antialiased`}>
      <body className="flex min-h-full flex-col">{children}</body>
    </html>
  );
}
