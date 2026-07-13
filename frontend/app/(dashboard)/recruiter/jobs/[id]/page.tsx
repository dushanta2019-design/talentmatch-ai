"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api, type Job, type Match } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScoreRing } from "@/components/score-ring";
import { HumanReviewBanner } from "@/components/human-review-banner";

export default function JobRankingPage() {
  const { id } = useParams<{ id: string }>();
  const [job, setJob] = useState<Job | null>(null);
  const [matches, setMatches] = useState<Match[]>([]);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    const [j, m] = await Promise.all([
      api<Job>(`/jobs/${id}`),
      api<Match[]>(`/matches/job/${id}`),
    ]);
    setJob(j);
    setMatches(m);
  }, [id]);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 5000);
    return () => clearInterval(t);
  }, [refresh]);

  async function matchAll() {
    setBusy(true);
    try {
      await api("/matches/batch", {
        method: "POST",
        body: JSON.stringify({ job_id: id, limit: 100 }),
      });
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  if (!job) return <p className="text-sm text-gray-500">Loading…</p>;

  const parsed = job.parsed ?? {};

  return (
    <div className="space-y-6">
      <HumanReviewBanner />

      <Card>
        <CardHeader className="flex-row items-start justify-between">
          <div>
            <CardTitle className="text-lg">{job.title}</CardTitle>
            <p className="text-sm text-gray-500">{job.company ?? "—"}</p>
          </div>
          <Button onClick={matchAll} disabled={busy || job.status !== "ready"}>
            {busy ? "Queuing…" : "Match all resumes"}
          </Button>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {(parsed.required_skills ?? []).map((s: string) => (
            <Badge key={s} color="blue">{s}</Badge>
          ))}
          {(parsed.preferred_skills ?? []).map((s: string) => (
            <Badge key={s}>{s} (preferred)</Badge>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Ranked candidates ({matches.length})</CardTitle>
          <p className="text-sm text-gray-500">
            Sorted by AI match score. Open a match to review evidence, gaps,
            and approve/reject/override.
          </p>
        </CardHeader>
        <CardContent>
          {matches.length === 0 && (
            <p className="text-sm text-gray-500">
              No matches yet — click “Match all resumes”.
            </p>
          )}
          <ul className="divide-y divide-gray-100">
            {matches.map((m, i) => (
              <li key={m.id} className="flex items-center gap-4 py-3">
                <span className="w-6 text-sm font-semibold text-gray-400">#{i + 1}</span>
                <ScoreRing score={m.overall_score} size={52} />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">
                    {m.resume_file_name ?? m.resume_id.slice(0, 8)}
                  </p>
                  <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-gray-500">
                    {m.confidence && <Badge>{m.confidence} confidence</Badge>}
                    <Badge
                      color={
                        m.review_status === "approved" ? "green"
                        : m.review_status === "rejected" ? "red"
                        : m.review_status === "overridden" ? "amber" : "default"
                      }
                    >
                      {m.review_status}
                    </Badge>
                    {m.status !== "scored" && <Badge color="amber">{m.status}</Badge>}
                  </div>
                </div>
                <Link href={`/matches/${m.id}`}>
                  <Button variant="outline" size="sm">Review</Button>
                </Link>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
