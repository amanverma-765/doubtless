import type React from "react";
import { AlertTriangle, Trash2 } from "lucide-react";
import { Modal } from "@/components/common";

interface DeleteModalProps {
  isOpen: boolean;
  videoTitle: string;
  onConfirm: () => void;
  onCancel: () => void;
  isDeleting?: boolean;
}

export const DeleteModal: React.FC<DeleteModalProps> = ({
  isOpen,
  videoTitle,
  onConfirm,
  onCancel,
  isDeleting = false,
}) => {
  return (
    <Modal
      isOpen={isOpen}
      onClose={onCancel}
      isBusy={isDeleting}
      maxWidth="max-w-sm"
    >
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-xl bg-rose-50 border border-rose-100 flex items-center justify-center text-rose-600 shrink-0">
          <AlertTriangle className="w-5 h-5" />
        </div>
        <div>
          <h3 className="text-base font-semibold text-zinc-900 leading-tight">
            Delete Video
          </h3>
          <p className="text-xs text-zinc-500 mt-0.5">
            This action cannot be undone.
          </p>
        </div>
      </div>

      <p className="text-xs text-zinc-600 bg-[#faf9f7] border border-[#e5e2db] rounded-xl p-3 mb-5 leading-relaxed">
        Are you sure you want to permanently delete{" "}
        <strong className="text-zinc-900 font-semibold">"{videoTitle}"</strong> along with
        its transcoded HLS streams and chat history?
      </p>

      <div className="flex items-center justify-end gap-2.5">
        <button
          type="button"
          onClick={onCancel}
          disabled={isDeleting}
          className="px-4 py-2 text-xs font-semibold text-zinc-700 hover:text-zinc-900 bg-[#f4f2ee] hover:bg-[#eae7df] rounded-xl transition-colors cursor-pointer disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={onConfirm}
          disabled={isDeleting}
          className="px-4 py-2 text-xs font-semibold text-white bg-rose-600 hover:bg-rose-700 rounded-xl flex items-center gap-1.5 transition-all cursor-pointer shadow-xs disabled:opacity-50 active:scale-95"
        >
          <Trash2 className="w-3.5 h-3.5" />
          <span>{isDeleting ? "Deleting..." : "Delete Video"}</span>
        </button>
      </div>
    </Modal>
  );
};
