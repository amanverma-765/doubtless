export type VideoState = "idle" | "uploading" | "processing" | "ready" | "error";

export interface VideoStatus {
  state: VideoState;
  progress: number;
  id: string | null;
  playlist: string | null;
  error: string | null;
}

export interface VideoItem {
  id: string;
  title: string;
  filename?: string | null;
  task_id?: string | null;
  playlist: string | null;
  poster: string | null;
  status: "idle" | "uploading" | "processing" | "ready" | "error" | "cancelled";
  progress: number;
  error?: string | null;
  created_at: string;
}

export interface UploadAccepted {
  id: string;
  message?: string;
}

export interface UploadConfig {
  max_upload_bytes: number;
  allowed_extensions: string[];
}
