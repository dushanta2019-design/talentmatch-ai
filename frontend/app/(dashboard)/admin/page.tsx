"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Stats {
  users: number;
  resumes: number;
  jobs: number;
  matches_scored: number;
  matches_failed: number;
  matches_reviewed: number;
  feedback_items: number;
  avg_score: number;
}

interface AuditLog {
  id: string;
  event_type: string;
  entity_type: string;
  entity_id: string | null;
  model_version: string | null;
  created_at: string;
}

interface EvalRun {
  id: string;
  model_version: string;
  dataset_size: number;
  metrics: Record<string, number | null>;
  created_at: string;
}

export default function AdminDashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [evals, setEvals] = useState<EvalRun[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const [s, l, e] = await Promise.all([
      api<Stats>("/admin/stats"),
      api<AuditLog[]>("/admin/audit-logs?limit=50"),
      api<EvalRun[]>("/admin/evaluations"),
    ]);
    setStats(s);
    setLogs(l);
    setEvals(e);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function run(action: "evaluate" | "training") {
    setBusy(action);
    setMessage(null);
    try {
      if (action === "evaluate") {
        const r = await api<EvalRun>("/admin/evaluate", { method: "POST" });
        setMessage(`Evaluation complete over ${r.dataset_size} feedback items.`);
      } else {
        const r = await api<{ status: string; dataset_size: number }>(
          "/admin/training/export", { method: "POST" });
        setMessage(`Training export: ${r.status} (${r.dataset_size} examples).`);
      }
      await refresh();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Failed");
    } finally {
      setBusy(null);
    }
  }

  const tiles = stats
    ? [
        ["Users", stats.users],
        ["Resumes", stats.resumes],
        ["Jobs", stats.jobs],
        ["Matches scored", stats.matches_scored],
        ["Matches reviewed", stats.matches_reviewed],
        ["Feedback items", stats.feedback_items],
        ["Failed matches", stats.matches_failed],
        ["Avg score", stats.avg_score.toFixed(1)],
      ]
    : [];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {tiles.map(([label, value]) => (
          <Card key={label as string}>
            <CardContent className="p-4">
              <p className="text-xs text-gray-500">{label}</p>
              <p className="text-2xl font-semibold">{value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <div>
            <CardTitle>Model operations</CardTitle>
            <p className="text-sm text-gray-500">
              Evaluate scoring quality against recruiter feedback, or export a
              privacy-checked dataset for fine-tuning.
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" disabled={busy !== null} onClick={() => run("evaluate")}>
              {busy === "evaluate" ? "Running…" : "Run evaluation"}
            </Button>
            <Button disabled={busy !== null} onClick={() => run("training")}>
              {busy === "training" ? "Exporting…" : "Export training data"}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {message && <p className="mb-3 text-sm text-brand-700">{message}</p>}
          {evals.length > 0 && (
            <table className="w-full text-left text-sm">
              <thead className="text-xs text-gray-500">
                <tr>
                  <th className="py-1">When</th>
                  <th>Model version</th>
                  <th>N</th>
                  <th>MAE</th>
                  <th>Agreement</th>
                  <th>P@5</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {evals.map((e) => (
                  <tr key={e.id}>
                    <td className="py-2">{new Date(e.created_at).toLocaleString()}</td>
                    <td className="max-w-[220px] truncate text-xs">{e.model_version}</td>
                    <td>{e.dataset_size}</td>
                    <td>{e.metrics.mae ?? "—"}</td>
                    <td>{e.metrics.agreement_rate ?? "—"}</td>
                    <td>{e.metrics.precision_at_5 ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Audit trail</CardTitle>
          <p className="text-sm text-gray-500">
            Every AI parse, match, and human review is logged with the model
            version and a hash of its (redacted) inputs.
          </p>
        </CardHeader>
        <CardContent>
          <ul className="divide-y divide-gray-100 text-sm">
            {logs.map((l) => (
              <li key={l.id} className="flex items-center justify-between py-2">
                <div className="flex items-center gap-2">
                  <Badge color="blue">{l.event_type}</Badge>
                  <span className="text-gray-500">
                    {l.entity_type} {l.entity_id?.slice(0, 8)}
                  </span>
                </div>
                <span className="text-xs text-gray-400">
                  {new Date(l.created_at).toLocaleString()}
                </span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
