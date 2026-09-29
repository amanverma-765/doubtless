import { describe, expect, it, vi } from "vitest";
import {
  deleteVideo,
  fetchUploadConfig,
  fetchVideoById,
  fetchVideos,
  fetchVideoStatus,
  uploadVideo,
} from "@/services/videoService";

describe("videoService", () => {
  it("fetchVideos returns list of videos", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => [
          {
            id: "vid-1",
            title: "Physics",
            filename: "vid-1.mp4",
            status: "ready",
            progress: 1.0,
          },
        ],
      })
    );

    const videos = await fetchVideos();
    expect(videos).toHaveLength(1);
    expect(videos[0].title).toBe("Physics");
  });

  it("fetchVideoById returns video details", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          id: "vid-123",
          title: "Chemistry",
          filename: "vid-123.mp4",
          status: "ready",
          progress: 1.0,
        }),
      })
    );

    const video = await fetchVideoById("vid-123");
    expect(video.id).toBe("vid-123");
    expect(video.title).toBe("Chemistry");
  });

  it("fetchVideoStatus returns current status payload", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          state: "processing",
          progress: 0.65,
          stage: "transcribing",
          stage_message: "Transcribing speech",
        }),
      })
    );

    const status = await fetchVideoStatus("vid-123");
    expect(status.state).toBe("processing");
    expect(status.progress).toBe(0.65);
  });

  it("fetchUploadConfig returns fallback config when fetch fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => ({}),
      })
    );

    const config = await fetchUploadConfig();
    expect(config.allowed_extensions).toContain("mp4");
    expect(config.max_upload_bytes).toBeGreaterThan(0);
  });

  it("deleteVideo sends DELETE request", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ id: "vid-del", status: "deleted" }),
    });
    vi.stubGlobal("fetch", mockFetch);

    await deleteVideo("vid-del");
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/videos/vid-del"),
      expect.objectContaining({ method: "DELETE" })
    );
  });

  it("uploadVideo sends file and tracks progress via XHR", async () => {
    let progressValue = 0;

    class MockXHR {
      static lastInstance: MockXHR | null = null;
      open = vi.fn();
      send = vi.fn().mockImplementation(() => {
        const inst = MockXHR.lastInstance;
        if (inst?.upload?.onprogress) {
          inst.upload.onprogress({ lengthComputable: true, loaded: 50, total: 100 });
        }
        if (inst) {
          inst.status = 200;
          inst.responseText = JSON.stringify({ id: "vid-uploaded" });
          if (inst.onload) {
            inst.onload();
          }
        }
      });
      upload: any = {};
      onload: (() => void) | null = null;
      onerror: (() => void) | null = null;
      abort = vi.fn();
      status = 200;
      statusText = "OK";
      responseText = "";

      constructor() {
        MockXHR.lastInstance = this;
      }
    }
    vi.stubGlobal("XMLHttpRequest", MockXHR);

    const dummyFile = new File(["dummy content"], "lecture.mp4", { type: "video/mp4" });
    const result = await uploadVideo(
      dummyFile,
      "My Lecture",
      (p) => {
        progressValue = p;
      }
    );

    expect(MockXHR.lastInstance!.open).toHaveBeenCalledWith(
      "PUT",
      expect.stringContaining("name=lecture.mp4&title=My%20Lecture")
    );
    expect(progressValue).toBe(0.5);
    expect(result.id).toBe("vid-uploaded");
  });

  it("uploadVideo aborts when AbortSignal triggers", async () => {
    class MockXHR {
      static lastInstance: MockXHR | null = null;
      open = vi.fn();
      send = vi.fn();
      upload: any = {};
      onload: (() => void) | null = null;
      onerror: (() => void) | null = null;
      abort = vi.fn();
      status = 0;
      statusText = "";
      responseText = "";

      constructor() {
        MockXHR.lastInstance = this;
      }
    }
    vi.stubGlobal("XMLHttpRequest", MockXHR);

    const controller = new AbortController();
    const dummyFile = new File(["dummy"], "cancel.mp4", { type: "video/mp4" });

    const promise = uploadVideo(dummyFile, "Cancel Lecture", undefined, controller.signal);
    controller.abort();

    await expect(promise).rejects.toThrow(/canceled/i);
    expect(MockXHR.lastInstance!.abort).toHaveBeenCalled();
  });

  it("uploadVideo rejects on HTTP error", async () => {
    class MockXHR {
      open = vi.fn();
      send = vi.fn().mockImplementation(() => {
        this.status = 413;
        this.statusText = "Payload Too Large";
        this.responseText = JSON.stringify({ detail: "File exceeds 500MB limit" });
        if (this.onload) {
          this.onload();
        }
      });
      upload: any = {};
      onload: (() => void) | null = null;
      onerror: (() => void) | null = null;
      abort = vi.fn();
      status = 413;
      statusText = "Payload Too Large";
      responseText = "";
    }
    vi.stubGlobal("XMLHttpRequest", MockXHR);

    const dummyFile = new File(["dummy"], "big.mp4", { type: "video/mp4" });
    await expect(uploadVideo(dummyFile)).rejects.toThrow("File exceeds 500MB limit");
  });
});
