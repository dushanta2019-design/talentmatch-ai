"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getSession } from "@/lib/api";

const HOME_BY_ROLE: Record<string, string> = {
  admin: "/admin",
  recruiter: "/recruiter",
  hiring_manager: "/recruiter",
  candidate: "/candidate",
};

export default function Home() {
  const router = useRouter();
  useEffect(() => {
    const session = getSession();
    router.replace(session ? (HOME_BY_ROLE[session.role] ?? "/login") : "/login");
  }, [router]);
  return null;
}
