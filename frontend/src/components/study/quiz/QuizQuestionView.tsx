import type React from "react";
import {
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Play,
  RotateCcw,
  XCircle,
} from "lucide-react";
import type { QuizQuestion } from "@/types/study";
import { formatTimestamp } from "@/utils/time";

interface QuizQuestionViewProps {
  question: QuizQuestion;
  currentIndex: number;
  totalQuestions: number;
  answeredCount: number;
  selectedOptionIndex: number | undefined;
  onSelectOption: (optionIndex: number) => void;
  onNext: () => void;
  onPrevious: () => void;
  onRestart: () => void;
  onSeek?: (seconds: number) => void;
}

const OPTION_LETTERS = ["A", "B", "C", "D"];

export const QuizQuestionView: React.FC<QuizQuestionViewProps> = ({
  question,
  currentIndex,
  totalQuestions,
  answeredCount,
  selectedOptionIndex,
  onSelectOption,
  onNext,
  onPrevious,
  onRestart,
  onSeek,
}) => {
  const hasAnsweredCurrent = selectedOptionIndex !== undefined;

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-5 flex flex-col justify-between bg-[#faf9f7] thin-scrollbar select-none">
      {/* Top Header & Progress */}
      <div className="space-y-3 pb-3 border-b border-[#e5e2db]">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-semibold tracking-wider text-zinc-500 uppercase">
            Question {currentIndex + 1} of {totalQuestions}
          </span>
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-zinc-400 font-medium">
              {answeredCount}/{totalQuestions} Answered
            </span>
            <button
              type="button"
              onClick={onRestart}
              title="Reset Quiz"
              className="w-6 h-6 rounded-md hover:bg-zinc-200/60 flex items-center justify-center text-zinc-400 hover:text-zinc-700 transition-colors cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Linear progress bar */}
        <div className="w-full h-1 bg-[#e5e2db] rounded-full overflow-hidden">
          <div
            className="h-full bg-indigo-600 rounded-full transition-all duration-300"
            style={{ width: `${((currentIndex + 1) / totalQuestions) * 100}%` }}
          />
        </div>
      </div>

      {/* Main Question Body */}
      <div className="flex-1 py-4 space-y-4">
        {/* Question text & optional timestamp seek button */}
        <div className="space-y-2">
          <div className="flex items-start justify-between gap-2">
            <h4 className="text-[14.5px] font-semibold text-zinc-900 leading-snug">
              {question.question}
            </h4>
            {question.timestamp !== null && question.timestamp !== undefined && (
              <button
                type="button"
                onClick={() => onSeek?.(question.timestamp!)}
                className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-mono text-[11px] font-semibold shrink-0 transition-all border border-indigo-200/80 active:scale-95 cursor-pointer"
                title={`Jump video to ${formatTimestamp(question.timestamp)}`}
              >
                <Play className="w-2.5 h-2.5 fill-current ml-0.5" />
                <span>{formatTimestamp(question.timestamp)}</span>
              </button>
            )}
          </div>
        </div>

        {/* Options List */}
        <div className="space-y-2.5">
          {question.options.map((optionText, optIdx) => {
            const isSelected = selectedOptionIndex === optIdx;
            const isCorrect = optIdx === question.correct_index;

            let cardStyle =
              "bg-white border-[#e5e2db] text-zinc-800 hover:border-indigo-300 hover:bg-indigo-50/30 cursor-pointer shadow-2xs";

            if (hasAnsweredCurrent) {
              if (isCorrect) {
                cardStyle =
                  "bg-emerald-50/90 border-emerald-300 text-emerald-950 font-semibold ring-2 ring-emerald-500/20 shadow-xs";
              } else if (isSelected) {
                cardStyle =
                  "bg-rose-50/90 border-rose-300 text-rose-950 ring-2 ring-rose-500/20 shadow-xs";
              } else {
                cardStyle = "bg-white/60 border-[#e5e2db] text-zinc-400 opacity-60";
              }
            }

            return (
              <button
                key={optIdx}
                type="button"
                disabled={hasAnsweredCurrent}
                onClick={() => onSelectOption(optIdx)}
                className={`w-full p-3.5 rounded-xl border text-left flex items-start gap-3 transition-all duration-150 ${cardStyle}`}
              >
                <span
                  className={`w-6 h-6 rounded-lg text-xs font-semibold flex items-center justify-center shrink-0 transition-colors ${
                    hasAnsweredCurrent && isCorrect
                      ? "bg-emerald-600 text-white"
                      : hasAnsweredCurrent && isSelected
                      ? "bg-rose-600 text-white"
                      : "bg-[#f4f2ee] text-zinc-600 border border-[#e3e0d8]"
                  }`}
                >
                  {OPTION_LETTERS[optIdx]}
                </span>

                <span className="flex-1 text-[13px] leading-relaxed pt-0.5">
                  {optionText}
                </span>

                {hasAnsweredCurrent && isCorrect && (
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                )}
                {hasAnsweredCurrent && isSelected && !isCorrect && (
                  <XCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                )}
              </button>
            );
          })}
        </div>

        {/* Explanation Card */}
        {hasAnsweredCurrent && (
          <div className="p-3.5 rounded-xl bg-white border border-indigo-100 shadow-2xs space-y-2 animate-in fade-in duration-150 text-left">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-indigo-900 uppercase tracking-wider">
                {selectedOptionIndex === question.correct_index
                  ? "✓ Correct Answer"
                  : "✗ Incorrect"}
              </span>
              {question.timestamp !== null && question.timestamp !== undefined && (
                <button
                  type="button"
                  onClick={() => onSeek?.(question.timestamp!)}
                  className="text-[11px] font-medium text-indigo-600 hover:text-indigo-800 flex items-center gap-1 cursor-pointer"
                >
                  <Play className="w-2.5 h-2.5 fill-current" />
                  Review in lecture [{formatTimestamp(question.timestamp)}]
                </button>
              )}
            </div>
            <p className="text-xs text-zinc-600 leading-relaxed">
              {question.explanation}
            </p>
          </div>
        )}
      </div>

      {/* Navigation Footer */}
      <div className="flex items-center justify-between pt-3 border-t border-[#e5e2db]">
        <button
          type="button"
          onClick={onPrevious}
          disabled={currentIndex === 0}
          className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold text-zinc-600 hover:text-zinc-900 disabled:opacity-30 disabled:cursor-not-allowed transition-colors cursor-pointer"
        >
          <ChevronLeft className="w-4 h-4" />
          <span>Previous</span>
        </button>

        {hasAnsweredCurrent && (
          <button
            type="button"
            onClick={onNext}
            className="inline-flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 active:scale-95 rounded-full transition-all shadow-xs cursor-pointer animate-in fade-in"
          >
            <span>
              {currentIndex === totalQuestions - 1 ? "View Results" : "Next Question"}
            </span>
            <ChevronRight className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
};
