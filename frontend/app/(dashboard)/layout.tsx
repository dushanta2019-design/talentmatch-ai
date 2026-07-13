"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getSession, setSession, type Session } from "@/lib/api";
import { Button } from "@/components/ui/button";

const NAV: Record<string, { href: string; label: string }[]> = {
  candidate: [{ href: "/candidate", label: "My Dashboard" }],
  recruiter: [{ href: "/recruiter", label: "Jobs & Candidates" }],
  hiring_manager: [{ href: "/recruiter", label: "Jobs & Candidates" }],
  admin: [
    { href: "/admin", label: "Admin" },
    { href: "/recruiter", label: "Jobs & Candidates" },
  ],
};

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [session, setLocal] = useState<Session | null>(null);

  useEffect(() => {
    const s = getSession();
    if (!s) router.replace("/login");
    else setLocal(s);
  }, [router]);

  if (!session) return null;

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-6">
            <span className="font-semibold text-brand-700">TalentMatch AI</span>
            <nav className="hidden gap-4 sm:flex">
              {(NAV[session.role] ?? []).map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="text-sm text-gray-600 hover:text-gray-900"
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden text-sm text-gray-500 sm:inline">
              {session.full_name} · {session.role.replace("_", " ")}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setSession(null);
                router.push("/login");
              }}
            >
              Sign out
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
    </div>
  );
}
