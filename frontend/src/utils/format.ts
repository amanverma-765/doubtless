/**
 * Centralized formatting utilities for video processing stages and labels.
 */

export function formatStageLabel(
  stage?: string | null,
  progress: number = 0
): string {
  const pct = `${Math.round(progress * 100)}%`;
  switch (stage) {
    case "transcribing":
      return `Transcribing speech (GPU) ${pct}`;
    case "indexing":
      return `Indexing vectors ${pct}`;
    case "generating_notes":
      return `Generating study notes ${pct}`;
    case "uploading":
      return `Uploading ${pct}`;
    case "transcoding":
    default:
      return `Transcoding video (HLS) ${pct}`;
  }
}
