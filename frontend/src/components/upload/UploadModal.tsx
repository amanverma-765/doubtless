import type React from "react";
import { useEffect, useState, useRef } from "react";
import { Film, Upload, AlertCircle, Loader2 } from "lucide-react";
import {
  formatFileSize,
  DEFAULT_MAX_UPLOAD_BYTES,
  DEFAULT_ALLOWED_EXTENSIONS,
} from "@/constants/config";
import { fetchUploadConfig } from "@/services/videoService";
import { Modal } from "@/components/common";

interface UploadModalProps {
  isOpen: boolean;
  file: File | null;
  onConfirm: (title: string) => void;
  onCancel: () => void;
  isUploading?: boolean;
  uploadProgress?: number;
}

export const UploadModal: React.FC<UploadModalProps> = ({
  isOpen,
  file,
  onConfirm,
  onCancel,
  isUploading = false,
  uploadProgress = 0,
}) => {
  const [title, setTitle] = useState("");
  const [maxBytes, setMaxBytes] = useState<number>(DEFAULT_MAX_UPLOAD_BYTES);
  const [allowedExtensions, setAllowedExtensions] = useState<string[]>(
    DEFAULT_ALLOWED_EXTENSIONS
  );
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchUploadConfig().then((cfg) => {
      if (cfg?.max_upload_bytes) {
        setMaxBytes(cfg.max_upload_bytes);
      }
      if (cfg?.allowed_extensions?.length) {
        setAllowedExtensions(cfg.allowed_extensions);
      }
    });
  }, []);

  useEffect(() => {
    if (file) {
      const rawName = file.name.replace(/\.[^/.]+$/, "");
      const cleaned = rawName
        .replace(/[_-]+/g, " ")
        .replace(/\s+/g, " ")
        .trim();
      const formatted = cleaned
        ? cleaned
            .split(" ")
            .map((w) => (w ? w.charAt(0).toUpperCase() + w.slice(1) : ""))
            .join(" ")
        : rawName;
      setTitle(formatted || rawName);
    }
  }, [file]);

  useEffect(() => {
    if (isOpen && !isUploading) {
      setTimeout(() => {
        inputRef.current?.focus();
        inputRef.current?.select();
      }, 50);
    }
  }, [isOpen, isUploading]);

  if (!isOpen || !file) return null;

  const fileExt = file.name.includes(".")
    ? file.name.split(".").pop()?.toLowerCase() || ""
    : "";
  const isUnsupportedExt = fileExt ? !allowedExtensions.includes(fileExt) : false;
  const isOverSize = file.size > maxBytes;
  const isInvalid = isOverSize || isUnsupportedExt;

  const formattedSize = formatFileSize(file.size);
  const formattedMaxSize = formatFileSize(maxBytes);
  const pctText = `${Math.round(uploadProgress * 100)}%`;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isInvalid || isUploading) return;
    const finalTitle = title.trim() || file.name.replace(/\.[^/.]+$/, "");
    onConfirm(finalTitle);
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onCancel}
      isBusy={isUploading}
      maxWidth="max-w-md"
    >
      <div className="flex items-center gap-3 mb-5">
        <div className="w-10 h-10 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600">
          <Film className="w-5 h-5" />
        </div>
        <div>
          <h3 className="text-xl font-serif italic text-zinc-900 leading-none">
            Upload Video
          </h3>
          <p className="text-xs text-zinc-500 mt-1 font-medium">
            Give your video a clear title for the library.
          </p>
        </div>
      </div>

      {/* File Details preview */}
      <div
        className={`border rounded-xl p-3 flex items-center justify-between text-xs transition-colors ${
          isInvalid
            ? "bg-rose-50/70 border-rose-200 text-rose-900"
            : "bg-[#faf9f7] border-[#e5e2db] text-zinc-600"
        }`}
      >
        <div className="flex items-center gap-2.5 truncate">
          <Film
            className={`w-4 h-4 shrink-0 ${
              isInvalid ? "text-rose-500" : "text-zinc-400"
            }`}
          />
          <span className="font-medium text-zinc-900 truncate">
            {file.name}
          </span>
        </div>
        <span
          className={`font-mono shrink-0 ml-2 font-semibold ${
            isInvalid ? "text-rose-600" : "text-zinc-500"
          }`}
        >
          {formattedSize}
        </span>
      </div>

      {/* Constraints Warning Alert */}
      {isUnsupportedExt && (
        <div className="mt-3 p-2.5 bg-rose-50 border border-rose-200 text-rose-800 rounded-xl flex items-center gap-2 text-xs">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>
            Unsupported format (.{fileExt}). Allowed:{" "}
            {allowedExtensions.join(", ")}
          </span>
        </div>
      )}

      {isOverSize && (
        <div className="mt-3 p-2.5 bg-rose-50 border border-rose-200 text-rose-800 rounded-xl flex items-center gap-2 text-xs">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>
            File is too large ({formattedSize}). Max size is {formattedMaxSize}.
          </span>
        </div>
      )}

      {/* Upload Progress Bar if active */}
      {isUploading && (
        <div className="mt-4 p-3 bg-indigo-50/60 border border-indigo-100 rounded-xl space-y-1.5">
          <div className="flex items-center justify-between text-xs font-semibold text-indigo-950">
            <span>Uploading media chunks…</span>
            <span className="font-mono">{pctText}</span>
          </div>
          <div className="w-full bg-indigo-200/60 h-1.5 rounded-full overflow-hidden">
            <div
              className="bg-indigo-600 h-full rounded-full transition-all duration-150"
              style={{ width: `${Math.round(uploadProgress * 100)}%` }}
            />
          </div>
        </div>
      )}

      {/* Edit Title Form */}
      <form onSubmit={handleSubmit} className="mt-4 space-y-4">
        <div>
          <label
            htmlFor="video-title-input"
            className="block text-xs font-semibold text-zinc-900 mb-1.5 uppercase tracking-wider"
          >
            Video Title
          </label>
          <input
            id="video-title-input"
            ref={inputRef}
            type="text"
            required
            disabled={isUploading}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Introduction to Quantum Computing"
            className="w-full px-3.5 py-2.5 text-sm bg-white border border-[#d5d1c7] rounded-xl focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-500/20 text-zinc-900 transition-all placeholder:text-zinc-400 disabled:bg-zinc-50 disabled:text-zinc-500 shadow-2xs"
          />
        </div>

        <div className="flex items-center justify-end gap-2.5 pt-2">
          <button
            type="button"
            onClick={onCancel}
            disabled={isUploading}
            className="px-4 py-2 text-xs font-semibold text-zinc-700 hover:text-zinc-900 bg-[#f4f2ee] hover:bg-[#eae7df] rounded-xl transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isInvalid || !title.trim() || isUploading}
            className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl flex items-center gap-1.5 transition-all cursor-pointer shadow-xs active:scale-95"
          >
            {isUploading ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Uploading ({pctText})…</span>
              </>
            ) : (
              <>
                <Upload className="w-3.5 h-3.5" />
                <span>Upload & Transcode</span>
              </>
            )}
          </button>
        </div>
      </form>
    </Modal>
  );
};
