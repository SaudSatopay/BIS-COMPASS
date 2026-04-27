import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "BIS Compass — Find Your Indian Standard in Seconds",
  description:
    "AI-powered recommendation engine for Bureau of Indian Standards (BIS). Built for MSE compliance — describe your product, get the right IS codes instantly.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body>{children}</body>
    </html>
  );
}
