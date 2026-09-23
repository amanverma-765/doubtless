import type React from "react";
import { Award, RotateCcw } from "lucide-react";

interface QuizResultsViewProps {
  score: number;
  totalQuestions: number;
  onRestart: () => void;
}

export const QuizResultsView: React.FC<QuizResultsViewProps> = ({
  score,
  totalQuestions,
  onRestart,
}) => {
  const pct = Math.round((score / totalQuestions) * 100);

  return (
    <div className="flex-1 overflow-y-auto p-5 flex flex-col items-center justify-center text-center bg-[#faf9f7] thin-scrollbar">
      <div className="w-14 h-14 rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 mb-4 shadow-2xs">
        <Award className="w-7 h-7" />
      </div>

      <h3 className="text-lg font-serif italic text-zinc-900 font-semibold mb-1">
        Quiz Completed!
      </h3>
      <p className="text-xs text-zinc-500 mb-5 max-w-xs leading-relaxed">
        {pct >= 80
          ? "Excellent understanding! You've mastered the core concepts of this lecture."
          : pct >= 50
          ? "Good effort! Review the timestamps below to reinforce key concepts."
          : "Keep practicing! Review the lecture sections and try the quiz again."}
      </p>

      {/* Score Card */}
      <div className="bg-white border border-[#e5e2db] rounded-2xl p-4 w-full max-w-xs mb-6 shadow-2xs">
        <div className="text-3xl font-serif font-bold text-zinc-900 mb-1">
          {score} <span className="text-base font-normal text-zinc-400">/ {totalQuestions}</span>
        </div>
        <div className="text-xs font-semibold uppercase tracking-wider text-indigo-600">
          {pct}% Score
        </div>
      </div>

      <button
        type="button"
        onClick={onRestart}
        className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 active:scale-95 rounded-full transition-all shadow-xs cursor-pointer"
      >
        <RotateCcw className="w-3.5 h-3.5" />
        <span>Retake Quiz</span>
      </button>
    </div>
  );
};
