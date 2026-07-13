export function HumanReviewBanner() {
  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
      <strong>Decision support only.</strong> AI match scores highlight
      job-relevant evidence — they are not hiring decisions. A human reviewer
      must evaluate each candidate; scores never consider name, gender, age,
      or any other protected attribute.
    </div>
  );
}
