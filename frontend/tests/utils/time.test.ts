import { describe, expect, it } from "vitest";
import { formatTimestamp, parseTimeToSeconds } from "@/utils/time";

describe("formatTimestamp", () => {
  it("formats seconds less than an hour as mm:ss", () => {
    expect(formatTimestamp(0)).toBe("00:00");
    expect(formatTimestamp(65)).toBe("01:05");
    expect(formatTimestamp(599)).toBe("09:59");
  });

  it("formats seconds greater than or equal to an hour as hh:mm:ss", () => {
    expect(formatTimestamp(3600)).toBe("01:00:00");
    expect(formatTimestamp(3665)).toBe("01:01:05");
    expect(formatTimestamp(7322)).toBe("02:02:02");
  });

  it("handles negative numbers by clamping to 00:00", () => {
    expect(formatTimestamp(-10)).toBe("00:00");
  });
});

describe("parseTimeToSeconds", () => {
  it("parses mm:ss string into seconds", () => {
    expect(parseTimeToSeconds("01:30")).toBe(90);
    expect(parseTimeToSeconds("00:45")).toBe(45);
  });

  it("parses hh:mm:ss string into seconds", () => {
    expect(parseTimeToSeconds("01:01:05")).toBe(3665);
    expect(parseTimeToSeconds("02:00:00")).toBe(7200);
  });
});
