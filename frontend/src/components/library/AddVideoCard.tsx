import React, { useRef, useState } from "react";
import { Plus } from "lucide-react";

interface AddVideoCardProps {
  onFileSelect: (file: File) => void;
}

export const AddVideoCard: React.FC<AddVideoCardProps> = ({ onFileSelect }) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const dragCounterRef = useRef<number>(0);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      onFileSelect(e.target.files[0]);
      e.target.value = "";
    }
  };

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    dragCounterRef.current += 1;
    setIsDragOver(true);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    dragCounterRef.current -= 1;
    if (dragCounterRef.current <= 0) {
      dragCounterRef.current = 0;
      setIsDragOver(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    dragCounterRef.current = 0;
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      onFileSelect(e.dataTransfer.files[0]);
    }
  };

  return (
    <div
      onDragEnter={handleDragEnter}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={() => fileInputRef.current?.click()}
      className={`group relative rounded-xl border-2 border-dashed overflow-hidden transition-all duration-200 cursor-pointer flex flex-col select-none shadow-2xs ${
        isDragOver
          ? "border-[#4f46e5] bg-indigo-50/50 scale-[1.02]"
          : "border-[#d5d2cb] bg-white hover:border-[#4f46e5] hover:bg-[#faf9f6]"
      }`}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept="video/*,.mp4,.mkv,.webm,.mov,.avi,.m4v,.ts"
        className="hidden"
        onChange={handleFileChange}
      />

      {/* Top area matching aspect-video of thumbnail */}
      <div className="relative aspect-video w-full flex flex-col items-center justify-center gap-2.5 p-4">
        <div className="w-11 h-11 rounded-full bg-[#f0eee9] group-hover:bg-[#4f46e5] flex items-center justify-center transition-colors shadow-2xs">
          <Plus className="w-5 h-5 text-[#1f1f1f] group-hover:text-white transition-colors" />
        </div>
        <span className="text-[13.5px] font-semibold text-[#1f1f1f] group-hover:text-[#4f46e5] transition-colors">
          Add new video
        </span>
      </div>

      {/* Bottom area matching metadata footer */}
      <div className="p-3.5 flex flex-col justify-center flex-1 border-t border-dashed border-[#e2e0da] group-hover:border-[#4f46e5]/30 text-center bg-transparent">
        <span className="text-[11px] text-[#8a8880]">
          Click to browse or drop file
        </span>
      </div>
    </div>
  );
};
