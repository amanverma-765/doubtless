/**
 * Time formatting and parsing utilities for video and lecture timestamps.
 */

export function formatTimestamp(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  const hrs = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const rem = s % 60;
  if (hrs > 0) {
    return `${String(hrs).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(rem).padStart(2, "0")}`;
  }
  return `${String(m).padStart(2, "0")}:${String(rem).padStart(2, "0")}`;
}

export function parseTimeToSeconds(timeStr: string): number {
  return timeStr
    .split(":")
    .reduce((acc, v) => acc * 60 + (Number(v) || 0), 0);
}
