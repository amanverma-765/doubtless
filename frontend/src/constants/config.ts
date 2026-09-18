export const API_BASE = (
  (import.meta.env?.VITE_API_URL as string | undefined) || ""
).replace(/\/+$/, "");

export const DEFAULT_MAX_UPLOAD_BYTES = 4 * 1024 * 1024 * 1024; // 4 GB

export const DEFAULT_ALLOWED_EXTENSIONS = [
  "avi",
  "m4v",
  "mkv",
  "mov",
  "mp4",
  "ts",
  "webm",
];

export function formatFileSize(bytes: number): string {
  if (bytes >= 1024 * 1024 * 1024) {
    const gb = bytes / (1024 * 1024 * 1024);
    return `${gb % 1 === 0 ? gb.toFixed(0) : gb.toFixed(1)} GB`;
  }
  if (bytes >= 1024 * 1024) {
    const mb = bytes / (1024 * 1024);
    return `${mb % 1 === 0 ? mb.toFixed(0) : mb.toFixed(1)} MB`;
  }
  return `${Math.round(bytes / 1024)} KB`;
}
