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

export async function fetchVideos(): Promise<VideoItem[]> {
  return request<VideoItem[]>("/api/v1/videos", { cache: "no-store" });
}

export async function fetchVideoById(videoId: string): Promise<VideoItem> {
  return request<VideoItem>(`/api/v1/videos/${encodeURIComponent(videoId)}`, {
    cache: "no-store",
  });
}

export async function fetchVideoStatus(
  videoId?: string | null
): Promise<VideoStatus> {
  const path = videoId
    ? `/api/v1/videos/${encodeURIComponent(videoId)}/status`
    : "/api/v1/videos/status";
  return request<VideoStatus>(path, { cache: "no-store" });
}

let cachedConfig: UploadConfig | null = null;

export async function fetchUploadConfig(): Promise<UploadConfig> {
  if (cachedConfig) return cachedConfig;
  try {
    const config = await request<UploadConfig>("/api/v1/videos/config", {
      cache: "no-store",
    });
    cachedConfig = config;
    return config;
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

    const cleanup = () => {
      if (signal && abortHandler) {
        signal.removeEventListener("abort", abortHandler);
      }
    };

    if (xhr.upload && onProgress) {
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable && event.total > 0) {
          onProgress(event.loaded / event.total);
        }
      };
    }

    xhr.onload = () => {
      cleanup();
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const data = JSON.parse(xhr.responseText);
          if (data && data.id) {
            resolve(data);
          } else {
            reject(
              new Error("Server returned an invalid response without video ID.")
            );
          }
        } catch {
          reject(
            new Error(
              `Server returned unexpected response (status ${xhr.status}).`
            )
          );
        }
      } else {
        try {
          const err = JSON.parse(xhr.responseText);
          const detail = parseErrorDetail(err);
          reject(
            new Error(detail || `Upload failed with status ${xhr.status}`)
          );
        } catch {
          reject(new Error(`Upload failed with status ${xhr.status}`));
        }
      }
    };

    xhr.onerror = () => {
      cleanup();
      reject(new Error("Network error occurred during video upload."));
    };

    xhr.send(file);
  });
}
