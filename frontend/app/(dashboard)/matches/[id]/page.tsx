"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, getSession, type Match } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ScoreRing } from "@/components/score-ring";
import { HumanReviewBanner } from "@/components/human-review-banner";

function DimensionBar({ label, value }: { label: string; value: number | null }) {
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs text-gray-500">
        <span>{label}</span>
        <span>{value == null ? "—" : Math.round(value)}</span>
      </div>
      <div className="h-2 rounded-full bg-gray-100">
        <div
          className="h-2 rounded-full bg-brand-500"
          style={{ width: `${value ?? 0}%` }}
        />
      </div>
    </div>
  );
}

export default function MatchDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [match, setMatch] = useState<Match | null>(null);
  const [overrideScore, setOverrideScore] = useState("");
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const isReviewer = getSession()?.role !== "candidate";

  const refresh = useCallback(async () => {
    setMatch(await api<Match>(`/matches/${id}`));
  }, [id]);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 4000);
    return () => clearInterval(t);
  }, [refresh]);

  async function review(action: string) {
    setBusy(true);
    try {
      await api("/feedback", {
        method: "POST",
        body: JSON.stringify({
          match_id: id,
          action,
          label_score: action === "override" ? Number(overrideScore) : null,
          comment: comment || null,
        }),
      });
      setComment("");
      setOverrideScore("");
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  if (!match) return <p className="text-sm text-gray-500">Loading…</p>;

  const exp = match.explanation ?? {};

  return (
    <div className="space-y-6">
      <HumanReviewBanner />

      <Card>
        <CardHeader className="flex-row items-center gap-5">
          <ScoreRing score={match.overall_score} size={80} />
          <div>
            <CardTitle className="text-lg">Match report</CardTitle>
            <div className="mt-1 flex flex-wrap gap-2">
              {match.confidence && <Badge color="blue">{match.confidence} confidence</Badge>}
              <Badge
                color={
                  match.review_status === "approved" ? "green"
                  : match.review_status === "rejected" ? "red"
                  : match.review_status === "overridden" ? "amber" : "default"
                }
              >
                {match.review_status}
              </Badge>
              {match.override_score != null && (
                <Badge color="amber">human override: {match.override_score}</Badge>
              )}
              {match.status !== "scored" && <Badge color="amber">{match.status}</Badge>}
            </div>
          </div>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          <DimensionBar label="Semantic fit" value={match.semantic_score} />
          <DimensionBar label="Skills coverage" value={match.skills_score} />
          <DimensionBar label="Experience" value={match.experience_score} />
          <DimensionBar label="Education & certifications" value={match.education_score} />
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Matched skills</CardTitle></CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {(match.matched_skills ?? []).map((s) => <Badge key={s} color="green">{s}</Badge>)}
            {(match.matched_skills ?? []).length === 0 && (
              <p className="text-sm text-gray-500">None identified.</p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Missing skills</CardTitle></CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {(match.missing_skills ?? []).map((s) => <Badge key={s} color="red">{s}</Badge>)}
            {(match.missing_skills ?? []).length === 0 && (
              <p className="text-sm text-gray-500">No required skills missing.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Why this score — evidence for the reviewer</CardTitle></CardHeader>
        <CardContent className="space-y-4 text-sm">
          {exp.role_fit_summary && <p className="text-gray-700">{exp.role_fit_summary}</p>}
          {(exp.strengths ?? []).length > 0 && (
            <div>
              <h4 className="mb-1 font-medium text-emerald-700">Strengths</h4>
              <ul className="list-disc space-y-1 pl-5 text-gray-700">
                {exp.strengths!.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
            </div>
          )}
          {(exp.concerns ?? []).length > 0 && (
            <div>
              <h4 className="mb-1 font-medium text-rose-700">Concerns</h4>
              <ul className="list-disc space-y-1 pl-5 text-gray-700">
                {exp.concerns!.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
            </div>
          )}
          {(exp.experience_gaps ?? []).length > 0 && (
            <div>
              <h4 className="mb-1 font-medium text-amber-700">Experience gaps</h4>
              <ul className="list-disc space-y-1 pl-5 text-gray-700">
                {exp.experience_gaps!.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
            </div>
          )}
          {(exp.education_certification_gaps ?? []).length > 0 && (
            <div>
              <h4 className="mb-1 font-medium text-amber-700">Education & certification gaps</h4>
              <ul className="list-disc space-y-1 pl-5 text-gray-700">
                {exp.education_certification_gaps!.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
            </div>
          )}
          <p className="text-xs text-gray-400">{exp.recommendation_note}</p>
        </CardContent>
      </Card>

      {isReviewer && (
        <Card>
          <CardHeader>
            <CardTitle>Human review</CardTitle>
            <p className="text-sm text-gray-500">
              Your decision is recorded, audited, and (after privacy checks)
              used to improve the model.
            </p>
          </CardHeader>
          <CardContent className="space-y-3">
            <Textarea
              placeholder="Optional comment (no personal data, please)"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              rows={2}
            />
            <div className="flex flex-wrap items-center gap-2">
              <Button variant="success" disabled={busy} onClick={() => review("approve")}>
                Approve
              </Button>
              <Button variant="danger" disabled={busy} onClick={() => review("reject")}>
                Reject
              </Button>
              <div className="flex items-center gap-2">
                <Input
                  type="number" min={0} max={100} placeholder="0–100"
                  className="w-24"
                  value={overrideScore}
                  onChange={(e) => setOverrideScore(e.target.value)}
                />
                <Button
                  variant="outline"
                  disabled={busy || overrideScore === ""}
                  onClick={() => review("override")}
                >
                  Override score
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
