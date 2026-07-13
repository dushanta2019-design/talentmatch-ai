"use client";

export function ScoreRing({
  score,
  size = 64,
}: {
  score: number | null;
  size?: number;
}) {
  const value = score ?? 0;
  const r = size / 2 - 5;
  const circumference = 2 * Math.PI * r;
  const color =
    score == null
      ? "#9ca3af"
      : value >= 75
        ? "#059669"
        : value >= 50
          ? "#d97706"
          : "#e11d48";

  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e5e7eb" strokeWidth="5" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="5"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - value / 100)}
        />
      </svg>
      <span
        className="absolute inset-0 flex items-center justify-center text-sm font-bold"
        style={{ color }}
      >
        {score == null ? "…" : Math.round(value)}
      </span>
    </div>
  );
}
