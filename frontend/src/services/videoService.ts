import type {
  UploadAccepted,
  UploadConfig,
  VideoItem,
  VideoStatus,
} from "@/types/video";
import {
  API_BASE,
  DEFAULT_MAX_UPLOAD_BYTES,
  formatFileSize,
} from "@/constants/config";
import { request, parseErrorDetail } from "./client";

// Re-export study APIs for backward compatibility
export * from "./studyService";

export async function fetchVideos(): Promise<VideoItem[]> {
  return request<VideoItem[]>("/api/v1/videos", { cache: "no-store" });
}

export async function fetchVideoById(videoId: string): Promise<VideoItem> {
  return request<VideoItem>(`/api/v1/videos/${encodeURIComponent(videoId)}`, {
    cache: "no-store",
  });
}

export async function fetchVideoStatus(videoId: string): Promise<VideoStatus> {
  return request<VideoStatus>(
    `/api/v1/videos/${encodeURIComponent(videoId)}/status`,
    { cache: "no-store" }
  );
}

export async function fetchUploadConfig(): Promise<UploadConfig> {
  try {
    return await request<UploadConfig>("/api/v1/videos/config");
  } catch {
    return {
      max_upload_bytes: DEFAULT_MAX_UPLOAD_BYTES,
      allowed_extensions: ["mp4", "mkv", "mov", "webm", "m4v", "avi", "ts"],
    };
  }
}

export async function deleteVideo(videoId: string): Promise<void> {
  await request<{ status: string; id: string }>(
    `/api/v1/videos/${encodeURIComponent(videoId)}`,
    {
      method: "DELETE",
    }
  );
}

export function uploadVideo(
  file: File,
  title?: string,
  onProgress?: (progress: number) => void,
  signal?: AbortSignal,
  maxSizeBytes: number = DEFAULT_MAX_UPLOAD_BYTES
): Promise<UploadAccepted> {
  if (file.size > maxSizeBytes) {
    return Promise.reject(
      new Error(
        `File size (${formatFileSize(file.size)}) exceeds maximum allowed size of ${formatFileSize(maxSizeBytes)}.`
      )
    );
  }

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    let url = `${API_BASE}/api/v1/videos/upload?name=${encodeURIComponent(file.name)}`;
    if (title && title.trim()) {
      url += `&title=${encodeURIComponent(title.trim())}`;
    }

    xhr.open("PUT", url);

    let abortHandler: (() => void) | undefined;
    if (signal) {
      abortHandler = () => {
        xhr.abort();
        reject(new DOMException("Upload canceled by user", "AbortError"));
      };
      if (signal.aborted) {
        abortHandler();
        return;
      }
      signal.addEventListener("abort", abortHandler, { once: true });
    }

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) {
        const progress = Math.min(1, Math.max(0, event.loaded / event.total));
        onProgress(progress);
      }
    };

    xhr.onload = () => {
      if (signal && abortHandler) {
        signal.removeEventListener("abort", abortHandler);
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const res = JSON.parse(xhr.responseText) as UploadAccepted;
          resolve(res);
        } catch {
          resolve({ id: "" });
        }
      } else {
        let msg: string | undefined;
        try {
          const errJson = JSON.parse(xhr.responseText);
          msg = parseErrorDetail(errJson);
        } catch {
          // Response body is not JSON
        }
        reject(
          new Error(
            msg || `Upload failed with HTTP ${xhr.status}: ${xhr.statusText}`
          )
        );
      }
    };

    xhr.onerror = () => {
      if (signal && abortHandler) {
        signal.removeEventListener("abort", abortHandler);
      }
      reject(new Error("Network connection error during file upload."));
    };

    xhr.onabort = () => {
      if (signal && abortHandler) {
        signal.removeEventListener("abort", abortHandler);
      }
      reject(new DOMException("Upload canceled by user", "AbortError"));
    };

    xhr.send(file);
  });
}
