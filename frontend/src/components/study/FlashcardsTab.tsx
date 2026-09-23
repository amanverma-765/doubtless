import type React from "react";
import { useState, useEffect, useCallback } from "react";
import {
  Layers,
  RotateCw,
  Shuffle,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import type { VideoStatus } from "@/types/video";
import { useVideoFlashcards } from "@/hooks/useStudy";
import { FlashcardCard } from "./flashcards";
import { TabEmptyState } from "./TabEmptyState";

interface FlashcardsTabProps {
  videoId: string | null;
  currentTime?: number;
  onSeek?: (seconds: number) => void;
  status?: VideoStatus | null;
}

export const FlashcardsTab: React.FC<FlashcardsTabProps> = ({
  videoId,
  onSeek,
  status,
}) => {
  const { cards, loading, setCards } = useVideoFlashcards(videoId, status?.state);
  const [currentIndex, setCurrentIndex] = useState<number>(0);
  const [isFlipped, setIsFlipped] = useState<boolean>(false);
  const [masteredIds, setMasteredIds] = useState<Set<number>>(new Set());

  const isReady = status ? status.state === "ready" : !videoId;

  const handleFlip = useCallback(() => {
    setIsFlipped((prev) => !prev);
  }, []);

  const handleNext = useCallback(() => {
    if (cards.length === 0) return;
    setIsFlipped(false);
    setCurrentIndex((prev) => (prev + 1) % cards.length);
  }, [cards.length]);

  const handlePrev = useCallback(() => {
    if (cards.length === 0) return;
    setIsFlipped(false);
    setCurrentIndex((prev) => (prev - 1 + cards.length) % cards.length);
  }, [cards.length]);

  const handleShuffle = () => {
    setIsFlipped(false);
    setCurrentIndex(0);
    setCards((prev) => [...prev].sort(() => Math.random() - 0.5));
  };

  const toggleMastered = (id: number) => {
    setMasteredIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  // Keyboard navigation support
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }
      if (e.code === "Space") {
        e.preventDefault();
        handleFlip();
      } else if (e.code === "ArrowRight") {
        e.preventDefault();
        handleNext();
      } else if (e.code === "ArrowLeft") {
        e.preventDefault();
        handlePrev();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleFlip, handleNext, handlePrev]);

  if (loading && isReady) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-[#faf9f7]">
        <div className="w-8 h-8 rounded-full border-2 border-indigo-600 border-t-transparent animate-spin mb-3" />
        <p className="text-xs text-zinc-500">Loading revision flashcards…</p>
      </div>
    );
  }

  if (!isReady || cards.length === 0) {
    return (
      <TabEmptyState
        icon={Layers}
        title="Flashcards Not Ready"
        subtitle="Key revision flashcards will appear here once the video is processed."
        isProcessing={status?.state !== "ready"}
        stageMessage={status?.stage_message}
      />
    );
  }

  const currentCard = cards[currentIndex];
  const isMastered = masteredIds.has(currentCard.id);

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-5 flex flex-col justify-between bg-[#faf9f7] thin-scrollbar select-none">
      {/* Top Header Controls */}
      <div className="flex items-center justify-between pb-3 border-b border-[#e5e2db]">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-semibold tracking-wider text-zinc-500 uppercase">
            Card {currentIndex + 1} of {cards.length}
          </span>
          {masteredIds.size > 0 && (
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 font-semibold">
              {masteredIds.size} Mastered
            </span>
          )}
        </div>

        <button
          type="button"
          onClick={handleShuffle}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold text-zinc-600 hover:text-zinc-900 hover:bg-[#eae7df] rounded-lg transition-colors cursor-pointer"
          title="Shuffle cards"
        >
          <Shuffle className="w-3.5 h-3.5" />
          <span>Shuffle</span>
        </button>
      </div>

      {/* Main Flashcard View */}
      <FlashcardCard
        card={currentCard}
        isFlipped={isFlipped}
        isMastered={isMastered}
        onFlip={handleFlip}
        onToggleMastered={toggleMastered}
        onSeek={onSeek}
      />

      {/* Bottom Navigation Controls */}
      <div className="flex items-center justify-between pt-3 border-t border-[#e5e2db]">
        <button
          type="button"
          onClick={handlePrev}
          className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold text-zinc-600 hover:text-zinc-900 bg-white hover:bg-[#f4f2ee] border border-[#e5e2db] rounded-xl transition-all shadow-2xs cursor-pointer active:scale-95"
        >
          <ChevronLeft className="w-4 h-4" />
          <span>Previous</span>
        </button>

        <button
          type="button"
          onClick={handleFlip}
          className="inline-flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold text-zinc-800 bg-white hover:bg-[#f4f2ee] border border-[#d5d1c7] rounded-full transition-all shadow-2xs cursor-pointer active:scale-95"
        >
          <RotateCw className="w-3.5 h-3.5 text-indigo-600" />
          <span>{isFlipped ? "Flip to Front" : "Flip to Back"}</span>
        </button>

        <button
          type="button"
          onClick={handleNext}
          className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 border border-indigo-600 rounded-xl transition-all shadow-2xs cursor-pointer active:scale-95"
        >
          <span>Next</span>
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
