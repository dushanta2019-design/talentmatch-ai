"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, type Match, type Resume } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScoreRing } from "@/components/score-ring";

export default function CandidateDashboard() {
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [matches, setMatches] = useState<Match[]>([]);
  const [uploading, setUploading] = useState(false);
  const [matching, setMatching] = useState(false);

  const refresh = useCallback(async () => {
    const r = await api<Resume[]>("/resumes");
    setResumes(r);
    if (!selected && r.length > 0) setSelected(r[0].id);
  }, [selected]);

  const refreshMatches = useCallback(async () => {
    if (!selected) return;
    setMatches(await api<Match[]>(`/matches/resume/${selected}`));
  }, [selected]);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 5000);
    return () => clearInterval(t);
  }, [refresh]);

  useEffect(() => {
    refreshMatches();
    const t = setInterval(refreshMatches, 5000);
    return () => clearInterval(t);
  }, [refreshMatches]);

  async function upload(file: File) {
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const r = await api<Resume>("/resumes", { method: "POST", body: form });
      setSelected(r.id);
      await refresh();
    } finally {
      setUploading(false);
    }
  }

  async function findJobs() {
    if (!selected) return;
    setMatching(true);
    try {
      await api("/matches/batch", {
        method: "POST",
        body: JSON.stringify({ resume_id: selected, limit: 50 }),
      });
      await refreshMatches();
    } finally {
      setMatching(false);
    }
  }

  const current = resumes.find((r) => r.id === selected);

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900">
        Match scores show how your <strong>skills and experience</strong> line
        up with each role — they never consider personal characteristics, and
        recruiters always make the final call.
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card>
          <CardHeader><CardTitle>My resume</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <label className="flex h-24 cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 text-sm text-gray-500 hover:border-brand-500">
              {uploading ? "Uploading…" : "Upload resume (PDF/DOCX/TXT)"}
              <input type="file" className="hidden" accept=".pdf,.docx,.txt"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) upload(f);
                  e.target.value = "";
                }}
              />
            </label>
            {resumes.map((r) => (
              <button
                key={r.id}
                onClick={() => setSelected(r.id)}
                className={`flex w-full items-center justify-between rounded-md border px-3 py-2 text-left text-sm ${
                  r.id === selected ? "border-brand-500 bg-brand-50" : "border-gray-200"
                }`}
              >
                <span className="truncate">{r.file_name ?? r.id.slice(0, 8)}</span>
                <Badge color={r.status === "ready" ? "green" : r.status === "failed" ? "red" : "amber"}>
                  {r.status}
                </Badge>
              </button>
            ))}
            {current?.parsed && (
              <div className="pt-2">
                <p className="mb-1 text-xs font-medium text-gray-500">Skills detected</p>
                <div className="flex flex-wrap gap-1">
                  {(current.parsed.skills ?? []).slice(0, 15).map((s: string) => (
                    <Badge key={s}>{s}</Badge>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader className="flex-row items-center justify-between">
            <div>
              <CardTitle>Best-matching jobs</CardTitle>
              <p className="text-sm text-gray-500">Ranked by fit with your resume</p>
            </div>
            <Button onClick={findJobs} disabled={matching || current?.status !== "ready"}>
              {matching ? "Matching…" : "Find matching jobs"}
            </Button>
          </CardHeader>
          <CardContent>
            {matches.length === 0 && (
              <p className="text-sm text-gray-500">
                Upload a resume and click “Find matching jobs”.
              </p>
            )}
            <ul className="divide-y divide-gray-100">
              {matches.map((m) => (
                <li key={m.id} className="flex items-center gap-4 py-3">
                  <ScoreRing score={m.overall_score} size={52} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{m.job_title ?? "Job"}</p>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {(m.missing_skills ?? []).slice(0, 4).map((s) => (
                        <Badge key={s} color="amber">grow: {s}</Badge>
                      ))}
                    </div>
                  </div>
                  <Link href={`/matches/${m.id}`}>
                    <Button variant="outline" size="sm">Details</Button>
                  </Link>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
