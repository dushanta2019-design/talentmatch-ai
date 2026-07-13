import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TalentMatch AI",
  description: "AI-assisted resume and job matching — decision support for humans.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
