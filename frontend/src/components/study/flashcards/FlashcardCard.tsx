import type React from "react";
import { Check, Play, RotateCw } from "lucide-react";
import type { Flashcard } from "@/types/study";
import { formatTimestamp } from "@/utils/time";

interface FlashcardCardProps {
  card: Flashcard;
  isFlipped: boolean;
  isMastered: boolean;
  onFlip: () => void;
  onToggleMastered: (id: number) => void;
  onSeek?: (seconds: number) => void;
}

export const FlashcardCard: React.FC<FlashcardCardProps> = ({
  card,
  isFlipped,
  isMastered,
  onFlip,
  onToggleMastered,
  onSeek,
}) => {
  return (
    <div className="flex-1 py-4 flex flex-col items-center justify-center perspective-1000">
      <div
        onClick={onFlip}
        className={`relative w-full max-w-sm h-[230px] transition-transform duration-500 transform-style-preserve-3d will-change-transform cursor-pointer ${
          isFlipped ? "rotate-y-180" : ""
        }`}
      >
        {/* FRONT FACE */}
        <div className="absolute inset-0 w-full h-full bg-white border border-[#e2e0da] hover:border-indigo-300 rounded-2xl p-5 flex flex-col justify-between shadow-2xs hover:shadow-md transform-front backface-hidden text-left">
          {/* Top metadata */}
          <div className="flex items-center justify-between">
            <span className="text-[10.5px] font-semibold tracking-wider uppercase px-2.5 py-0.5 rounded-full bg-[#f4f2ee] text-indigo-700 border border-[#e3e0d8]">
              {card.category || "Concept"}
            </span>
            <span className="text-[11px] font-medium text-zinc-400 flex items-center gap-1">
              <RotateCw className="w-3 h-3" />
              Click to Flip
            </span>
          </div>

          {/* Prompt Content */}
          <div className="my-auto py-2">
            <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider block mb-1">
              Question / Term
            </span>
            <h4 className="text-[15px] font-semibold text-zinc-900 leading-snug">
              {card.front}
            </h4>
          </div>

          {/* Bottom Card Footer */}
          <div className="flex items-center justify-between pt-2 border-t border-[#f0eee9]">
            <span className="text-[11px] text-zinc-400">Click or press Space to flip</span>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onToggleMastered(card.id);
              }}
              className={`p-1.5 rounded-lg border text-xs font-semibold flex items-center gap-1 transition-colors cursor-pointer ${
                isMastered
                  ? "bg-emerald-600 text-white border-emerald-600 shadow-2xs"
                  : "bg-white text-zinc-400 hover:text-emerald-700 hover:bg-emerald-50 border-[#e5e2db]"
              }`}
              title={isMastered ? "Mark as unmastered" : "Mark as mastered"}
            >
              <Check className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* BACK FACE */}
        <div className="absolute inset-0 w-full h-full bg-white border border-indigo-200 rounded-2xl p-5 flex flex-col justify-between shadow-xs transform-back backface-hidden text-left">
          {/* Top metadata */}
          <div className="flex items-center justify-between">
            <span className="text-[10.5px] font-semibold tracking-wider uppercase px-2.5 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-100 font-semibold">
              Answer / Definition
            </span>
            <span className="text-[11px] font-medium text-indigo-600 flex items-center gap-1">
              <RotateCw className="w-3 h-3" />
              Click to Flip
            </span>
          </div>

          {/* Answer Content */}
          <div className="my-auto py-2 overflow-y-auto thin-scrollbar max-h-[110px]">
            <p className="text-[14px] text-zinc-800 leading-relaxed font-medium">
              {card.back}
            </p>
          </div>

          {/* Bottom Card Footer */}
          <div className="flex items-center justify-between pt-2 border-t border-[#f0eee9]">
            {card.timestamp !== null && card.timestamp !== undefined ? (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onSeek?.(card.timestamp!);
                }}
                className="inline-flex items-center gap-1 text-[11.5px] font-semibold text-indigo-600 hover:text-indigo-800 cursor-pointer"
              >
                <Play className="w-3 h-3 fill-current" />
                <span>Jump to lecture [{formatTimestamp(card.timestamp)}]</span>
              </button>
            ) : (
              <span className="text-[11px] text-zinc-400">Click to flip</span>
            )}

            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onToggleMastered(card.id);
              }}
              className={`p-1.5 rounded-lg border text-xs font-semibold flex items-center gap-1 transition-colors cursor-pointer ${
                isMastered
                  ? "bg-emerald-600 text-white border-emerald-600 shadow-2xs"
                  : "bg-white text-zinc-400 hover:text-emerald-700 hover:bg-emerald-50 border-[#e5e2db]"
              }`}
              title={isMastered ? "Mark as unmastered" : "Mark as mastered"}
            >
              <Check className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
