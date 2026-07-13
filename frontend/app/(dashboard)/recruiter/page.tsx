"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, type Job, type Resume } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { HumanReviewBanner } from "@/components/human-review-banner";

const statusColor = (s: string) =>
  s === "ready" ? "green" : s === "failed" ? "red" : "amber";

export default function RecruiterDashboard() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);

  const refresh = useCallback(async () => {
    const [j, r] = await Promise.all([api<Job[]>("/jobs"), api<Resume[]>("/resumes")]);
    setJobs(j);
    setResumes(r);
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 5000);
    return () => clearInterval(t);
  }, [refresh]);

  async function createJob(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api("/jobs", {
        method: "POST",
        body: JSON.stringify({ title, company: company || null, description }),
      });
      setTitle("");
      setCompany("");
      setDescription("");
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  async function uploadResume(file: File) {
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      await api("/resumes", { method: "POST", body: form });
      await refresh();
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="space-y-6">
      <HumanReviewBanner />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Create a job description</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={createJob} className="space-y-3">
              <Input placeholder="Job title" value={title}
                     onChange={(e) => setTitle(e.target.value)} required />
              <Input placeholder="Company (optional)" value={company}
                     onChange={(e) => setCompany(e.target.value)} />
              <Textarea placeholder="Paste the full job description…" value={description}
                        onChange={(e) => setDescription(e.target.value)} required rows={6} />
              <Button type="submit" disabled={busy}>
                {busy ? "Creating…" : "Create & parse"}
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Upload candidate resumes</CardTitle>
            <p className="text-sm text-gray-500">PDF, DOCX, or TXT · max 10 MB</p>
          </CardHeader>
          <CardContent>
            <label className="flex h-32 cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 text-sm text-gray-500 hover:border-brand-500">
              {uploading ? "Uploading…" : "Click to choose a resume file"}
              <input
                type="file"
                className="hidden"
                accept=".pdf,.docx,.txt"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) uploadResume(f);
                  e.target.value = "";
                }}
              />
            </label>
            <ul className="mt-4 max-h-48 space-y-2 overflow-y-auto">
              {resumes.map((r) => (
                <li key={r.id} className="flex items-center justify-between text-sm">
                  <span className="truncate">{r.file_name ?? r.id.slice(0, 8)}</span>
                  <Badge color={statusColor(r.status)}>{r.status}</Badge>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Jobs</CardTitle>
        </CardHeader>
        <CardContent>
          {jobs.length === 0 && (
            <p className="text-sm text-gray-500">No jobs yet — create one above.</p>
          )}
          <ul className="divide-y divide-gray-100">
            {jobs.map((j) => (
              <li key={j.id} className="flex items-center justify-between py-3">
                <div>
                  <Link
                    href={`/recruiter/jobs/${j.id}`}
                    className="font-medium text-brand-700 hover:underline"
                  >
                    {j.title}
                  </Link>
                  <p className="text-sm text-gray-500">
                    {j.company ?? "—"} {j.is_open ? "" : "· closed"}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <Badge color={statusColor(j.status)}>{j.status}</Badge>
                  <Link href={`/recruiter/jobs/${j.id}`}>
                    <Button variant="outline" size="sm">Rank candidates</Button>
                  </Link>
                </div>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
