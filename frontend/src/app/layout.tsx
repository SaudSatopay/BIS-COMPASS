import type { Metadata } from "next";
import { Bricolage_Grotesque, Instrument_Serif } from "next/font/google";
import "./globals.css";

const bricolage = Bricolage_Grotesque({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
  weight: ["400", "500", "600", "700", "800"],
});

const instrument = Instrument_Serif({
  subsets: ["latin"],
  variable: "--font-serif",
  display: "swap",
  weight: ["400"],
  style: ["italic"],
});

export const metadata: Metadata = {
  title: "BIS Compass — Find Your Indian Standard in Seconds",
  description:
    "AI-powered recommendation engine for Bureau of Indian Standards (BIS). Built for MSE compliance — describe your product, get the right IS codes instantly.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`dark ${bricolage.variable} ${instrument.variable}`}>
      <body>{children}</body>
    </html>
  );
}
