import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useVideoUpload } from "@/hooks/useVideoUpload";
import * as videoService from "@/services/videoService";

vi.mock("@/services/videoService", () => ({
  uploadVideo: vi.fn(),
}));

describe("useVideoUpload Hook", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("initializes with default state", () => {
    const { result } = renderHook(() => useVideoUpload());

    expect(result.current.pendingFile).toBeNull();
    expect(result.current.isUploading).toBe(false);
    expect(result.current.uploadProgress).toBe(0);
    expect(result.current.error).toBeNull();
  });

  it("selects and clears pending file", () => {
    const { result } = renderHook(() => useVideoUpload());
    const file = new File(["dummy"], "lecture.mp4", { type: "video/mp4" });

    act(() => {
      result.current.selectFile(file);
    });

    expect(result.current.pendingFile).toBe(file);

    act(() => {
      result.current.clearPendingFile();
    });

    expect(result.current.pendingFile).toBeNull();
  });

  it("handles successful video upload", async () => {
    const onSuccess = vi.fn();
    vi.mocked(videoService.uploadVideo).mockImplementation(
      async (_file, _title, onProgress) => {
        if (onProgress) onProgress(0.5);
        return { id: "vid-123" };
      }
    );

    const { result } = renderHook(() => useVideoUpload({ onSuccess }));
    const file = new File(["content"], "physics.mp4", { type: "video/mp4" });

    act(() => {
      result.current.selectFile(file);
    });

    await act(async () => {
      await result.current.confirmUpload("Physics 101");
    });

    expect(videoService.uploadVideo).toHaveBeenCalledWith(
      file,
      "Physics 101",
      expect.any(Function),
      expect.any(AbortSignal)
    );
    expect(onSuccess).toHaveBeenCalledWith("vid-123");
    expect(result.current.pendingFile).toBeNull();
    expect(result.current.isUploading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("captures upload failure and exposes error message", async () => {
    vi.mocked(videoService.uploadVideo).mockRejectedValue(
      new Error("Network timeout")
    );

    const { result } = renderHook(() => useVideoUpload());
    const file = new File(["content"], "calc.mp4", { type: "video/mp4" });

    act(() => {
      result.current.selectFile(file);
    });

    await act(async () => {
      await result.current.confirmUpload("Calculus");
    });

    expect(result.current.error).toBe("Network timeout");
    expect(result.current.isUploading).toBe(false);
    expect(result.current.uploadProgress).toBe(0);

    act(() => {
      result.current.clearError();
    });
    expect(result.current.error).toBeNull();
  });

  it("cancels active upload and resets state", () => {
    const { result } = renderHook(() => useVideoUpload());
    const file = new File(["content"], "cancel.mp4", { type: "video/mp4" });

    act(() => {
      result.current.selectFile(file);
      result.current.cancelUpload();
    });

    expect(result.current.pendingFile).toBeNull();
    expect(result.current.isUploading).toBe(false);
    expect(result.current.uploadProgress).toBe(0);
  });
});
