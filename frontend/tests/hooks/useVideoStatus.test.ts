import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useVideoStatus } from "@/hooks/useVideoStatus";
import * as videoService from "@/services/videoService";
import type { VideoStatus } from "@/types/video";

vi.mock("@/services/videoService", () => ({
  fetchVideoStatus: vi.fn(),
}));

describe("useVideoStatus Hook", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("handles empty or null videoId", () => {
    const { result } = renderHook(() => useVideoStatus(null));

    expect(result.current.status).toBeNull();
    expect(result.current.isLoading).toBe(false);
    expect(result.current.isNotFound).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("fetches and sets video status for a valid videoId", async () => {
    const mockStatus: VideoStatus = {
      state: "ready",
      progress: 1.0,
      id: "vid-1",
      playlist: "/hls/vid-1/index.m3u8",
    };
    vi.mocked(videoService.fetchVideoStatus).mockResolvedValue(mockStatus);

    const { result } = renderHook(() => useVideoStatus("vid-1"));

    await waitFor(() => {
      expect(result.current.status).toEqual(mockStatus);
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.isNotFound).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("detects not found condition when state is idle with no id", async () => {
    vi.mocked(videoService.fetchVideoStatus).mockResolvedValue({
      state: "idle",
      progress: 0,
    });

    const { result } = renderHook(() => useVideoStatus("missing-vid"));

    await waitFor(() => {
      expect(result.current.isNotFound).toBe(true);
    });

    expect(result.current.status?.state).toBe("idle");
    expect(result.current.isLoading).toBe(false);
  });

  it("handles fetch rejection and populates error state", async () => {
    vi.mocked(videoService.fetchVideoStatus).mockRejectedValue(
      new Error("Server offline")
    );

    const { result } = renderHook(() => useVideoStatus("vid-err"));

    await waitFor(() => {
      expect(result.current.error).toBe("Server offline");
    });

    expect(result.current.isLoading).toBe(false);
  });

  it("refetch manually invokes status fetch", async () => {
    const mockStatus: VideoStatus = {
      state: "processing",
      progress: 0.45,
      id: "vid-proc",
      stage: "transcribing",
    };
    vi.mocked(videoService.fetchVideoStatus).mockResolvedValue(mockStatus);

    const { result } = renderHook(() => useVideoStatus("vid-proc"));

    await waitFor(() => {
      expect(result.current.status?.progress).toBe(0.45);
    });

    const updatedStatus: VideoStatus = {
      state: "ready",
      progress: 1.0,
      id: "vid-proc",
    };
    vi.mocked(videoService.fetchVideoStatus).mockResolvedValue(updatedStatus);

    await act(async () => {
      await result.current.refetch();
    });

    expect(result.current.status?.state).toBe("ready");
    expect(result.current.status?.progress).toBe(1.0);
  });
});
