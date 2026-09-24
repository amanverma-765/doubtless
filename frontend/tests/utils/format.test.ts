import { describe, expect, it } from "vitest";
import { formatStageLabel } from "@/utils/format";

describe("formatStageLabel", () => {
  it("formats transcribing stage with percentage", () => {
    expect(formatStageLabel("transcribing", 0.45)).toBe(
      "Transcribing speech (GPU) 45%"
    );
  });

  it("formats indexing stage with percentage", () => {
    expect(formatStageLabel("indexing", 0.8)).toBe("Indexing vectors 80%");
  });

  it("formats generating_notes stage with percentage", () => {
    expect(formatStageLabel("generating_notes", 0.95)).toBe(
      "Generating study notes 95%"
    );
  });

  it("formats uploading stage with percentage", () => {
    expect(formatStageLabel("uploading", 0.1)).toBe("Uploading 10%");
  });

  it("defaults to transcoding stage when stage is null or unknown", () => {
    expect(formatStageLabel(null, 0.25)).toBe("Transcoding video (HLS) 25%");
    expect(formatStageLabel("unknown", 0.5)).toBe(
      "Transcoding video (HLS) 50%"
    );
  });
});
