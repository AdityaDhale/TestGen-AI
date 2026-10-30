import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TestGen AI — Auto Unit Test Generator | Powered by NVIDIA Nemotron",
  description:
    "Generate comprehensive unit tests automatically using NVIDIA Nemotron AI on Nebius AI Cloud. Paste your code, get professional tests in seconds.",
  keywords: ["unit testing", "AI", "NVIDIA Nemotron", "Nebius", "test generation", "pytest"],
  openGraph: {
    title: "TestGen AI — Auto Unit Test Generator",
    description: "AI-powered unit test generation with NVIDIA Nemotron on Nebius AI Cloud",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
