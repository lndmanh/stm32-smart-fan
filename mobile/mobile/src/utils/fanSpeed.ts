export function clampFanPercent(
  percent: number,
  min = 0,
  max = 100,
): number {
  const lo = Math.max(0, Math.min(100, Math.round(min)));
  const hi = Math.max(lo, Math.min(100, Math.round(max)));
  return Math.round(Math.max(lo, Math.min(hi, percent)));
}

export function buildFanPresets(min: number, max: number): number[] {
  const lo = Math.max(0, Math.min(100, Math.round(min)));
  const hi = Math.max(lo, Math.min(100, Math.round(max)));
  const candidates = [0, 30, 50, 70, 100, lo, hi].filter(
    (value) => value >= lo && value <= hi,
  );
  return [...new Set(candidates)].sort((a, b) => a - b);
}
