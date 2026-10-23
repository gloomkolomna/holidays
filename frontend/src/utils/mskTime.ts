export function msUntilNextMskMidnight(now: Date = new Date()): number {
  const mskWall = new Date(now.getTime() + (now.getTimezoneOffset() + 180) * 60000);
  const next = new Date(mskWall);
  next.setHours(24, 0, 0, 0);
  return Math.max(next.getTime() - mskWall.getTime(), 0);
}
