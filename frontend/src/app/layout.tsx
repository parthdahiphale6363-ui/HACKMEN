import type { Metadata, Viewport } from "next";
import "./globals.css";

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0b101b" },
  ],
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
};

export const metadata: Metadata = {
  title: "TruthLens AI — Multimodal Video Forensics & Fact-Checking Engine",
  description: "Detect synthetic audio, voice clones, and video manipulation with an 8-stage multimodal forensics pipeline, cross-platform OSINT data mining, and explainable AI verdicts.",
  applicationName: "TruthLens AI",
  authors: [{ name: "TruthLens AI Team" }],
  keywords: [
    "deepfake detection",
    "video forensics",
    "fact-checking",
    "multimodal AI",
    "OSINT",
    "media authenticity",
    "C2PA",
    "YouTube Shorts verification",
    "misinformation analysis",
  ],
  openGraph: {
    title: "TruthLens AI — Video Forensics & Fact-Checking Engine",
    description: "Real-time multimodal deepfake detection, speech forensics, and factual verification for viral short-form video content.",
    type: "website",
    locale: "en_US",
    siteName: "TruthLens AI",
  },
  twitter: {
    card: "summary_large_image",
    title: "TruthLens AI — Video Forensics & Fact-Checking Engine",
    description: "Multimodal audio-visual forensics, cross-platform OSINT signals, and live fact-checking for short-form media.",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body>{children}</body>
    </html>
  );
}
