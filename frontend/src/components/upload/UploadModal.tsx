import type React from "react";
import { useEffect, useState, useRef } from "react";
import { Film, Upload, X, AlertCircle, Loader2 } from "lucide-react";
import {
  formatFileSize,
  DEFAULT_MAX_UPLOAD_BYTES,
  DEFAULT_ALLOWED_EXTENSIONS,
} from "@/constants/config";
import { fetchUploadConfig } from "@/services/videoService";

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

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen || isUploading) return;
      if (e.key === "Escape") {
        onCancel();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, isUploading, onCancel]);

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
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs animate-in fade-in duration-150"
      onClick={() => {
        if (!isUploading) onCancel();
      }}
    >
      <div
        className="bg-white border border-[#e2e0da] rounded-2xl shadow-2xl max-w-md w-full p-6 text-left relative"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          onClick={onCancel}
          disabled={isUploading}
          className="absolute top-4 right-4 w-8 h-8 rounded-full flex items-center justify-center text-[#8a8880] hover:text-[#1f1f1f] hover:bg-[#f0eee9] transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <X className="w-4 h-4" />
        </button>

        <div className="flex items-center gap-3 mb-5">
          <div className="w-10 h-10 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-[#4f46e5]">
            <Film className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-serif italic text-[#1f1f1f] leading-none">
              Upload Video
            </h3>
            <p className="text-xs text-[#6b6b6b] mt-1 font-medium">
              Give your video a clear title for the library.
            </p>
          </div>
        </div>

        {/* File Details preview */}
        <div
          className={`border rounded-xl p-3 flex items-center justify-between text-xs transition-colors ${
            isInvalid
              ? "border-rose-200 bg-rose-50/40 text-[#6b6b6b] mb-2"
              : "border-[#e8e6df] bg-[#faf9f6] text-[#6b6b6b] mb-4"
          }`}
        >
          <div className="truncate pr-2 min-w-0">
            <span className="font-semibold text-[#1f1f1f] block truncate">
              {file.name}
            </span>
          </div>
          <span
            className={`text-[11px] font-medium whitespace-nowrap px-2 py-0.5 rounded border shrink-0 ${
              isInvalid
                ? "bg-rose-100 text-rose-700 border-rose-300 font-semibold"
                : "bg-white text-[#8a8880] border-[#e2e0da]"
            }`}
          >
            {formattedSize}
          </span>
        </div>

        {isOverSize && (
          <p className="text-xs text-rose-600 mb-3 font-medium flex items-center gap-1.5">
            <AlertCircle className="w-3.5 h-3.5 shrink-0 text-rose-500" />
            <span>
              File size exceeds maximum allowed limit of {formattedMaxSize}.
            </span>
          </p>
        )}

        {isUnsupportedExt && (
          <p className="text-xs text-rose-600 mb-3 font-medium flex items-center gap-1.5">
            <AlertCircle className="w-3.5 h-3.5 shrink-0 text-rose-500" />
            <span>
              Unsupported file format (.{fileExt}). Allowed formats:{" "}
              {allowedExtensions.map((e) => e.toUpperCase()).join(", ")}.
            </span>
          </p>
        )}

        {/* Upload Progress Bar when active */}
        {isUploading && (
          <div className="mb-4 bg-indigo-50/70 border border-indigo-100 rounded-xl p-3 space-y-2">
            <div className="flex items-center justify-between text-xs text-[#4f46e5] font-medium">
              <span className="flex items-center gap-1.5">
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Uploading raw video to server…
              </span>
              <span>{pctText}</span>
            </div>
            <div className="w-full h-1.5 bg-indigo-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-[#4f46e5] rounded-full transition-all duration-200"
                style={{ width: pctText }}
              />
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="video-title-input"
              className="block text-xs font-semibold text-[#1f1f1f] mb-1.5 uppercase tracking-wider"
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
              className="w-full px-3.5 py-2.5 text-sm bg-white border border-[#d5d2cb] rounded-lg focus:outline-none focus:border-[#4f46e5] focus:ring-2 focus:ring-[#4f46e5]/20 text-[#1f1f1f] transition-all placeholder:text-[#a19f96] disabled:bg-zinc-50 disabled:text-zinc-500"
            />
          </div>

          <div className="flex items-center justify-end gap-2.5 pt-2">
            <button
              type="button"
              onClick={onCancel}
              disabled={isUploading}
              className="px-4 py-2 text-xs font-medium text-[#6b6b6b] hover:text-[#1f1f1f] bg-[#f5f4f0] hover:bg-[#eae7df] rounded-lg transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isInvalid || !title.trim() || isUploading}
              className="px-4 py-2 text-xs font-semibold text-white bg-[#4f46e5] hover:bg-[#4338ca] disabled:opacity-50 disabled:cursor-not-allowed rounded-lg flex items-center gap-1.5 transition-colors cursor-pointer shadow-xs"
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
      </div>
    </div>
  );
};
