import type React from "react";
import { useState } from "react";
import { HelpCircle } from "lucide-react";
import type { VideoStatus } from "@/types/video";
import { useVideoQuiz } from "@/hooks/useStudy";
import { QuizQuestionView, QuizResultsView } from "./quiz";
import { TabEmptyState } from "./TabEmptyState";

interface QuizTabProps {
  videoId: string | null;
  currentTime?: number;
  onSeek?: (seconds: number) => void;
  status?: VideoStatus | null;
}

export const QuizTab: React.FC<QuizTabProps> = ({
  videoId,
  onSeek,
  status,
}) => {
  const { questions, loading } = useVideoQuiz(videoId, status?.state);
  const [currentIndex, setCurrentIndex] = useState<number>(0);
  const [selectedAnswers, setSelectedAnswers] = useState<Record<number, number>>({});
  const [isCompleted, setIsCompleted] = useState<boolean>(false);

  const isReady = status ? status.state === "ready" : !videoId;

  if (loading && isReady) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-[#faf9f7]">
        <div className="w-8 h-8 rounded-full border-2 border-indigo-600 border-t-transparent animate-spin mb-3" />
        <p className="text-xs text-zinc-500">Loading interactive quiz…</p>
      </div>
    );
  }

  if (!isReady || questions.length === 0) {
    return (
      <TabEmptyState
        icon={HelpCircle}
        title="Quiz Not Ready"
        subtitle="Interactive quiz questions will appear here once video processing completes."
      />
    );
  }

  const currentQ = questions[currentIndex];
  const totalQuestions = questions.length;
  const answeredCount = Object.keys(selectedAnswers).length;
  const selectedOptionIndex = selectedAnswers[currentIndex];

  const handleSelectOption = (optionIndex: number) => {
    if (selectedOptionIndex !== undefined) return;
    setSelectedAnswers((prev) => ({
      ...prev,
      [currentIndex]: optionIndex,
    }));
  };

  const handleNext = () => {
    if (currentIndex < totalQuestions - 1) {
      setCurrentIndex((prev) => prev + 1);
    } else {
      setIsCompleted(true);
    }
  };

  const handlePrevious = () => {
    if (currentIndex > 0) {
      setCurrentIndex((prev) => prev - 1);
    }
  };

  const handleRestart = () => {
    setSelectedAnswers({});
    setCurrentIndex(0);
    setIsCompleted(false);
  };

  const score = questions.reduce((acc, q, idx) => {
    return selectedAnswers[idx] === q.correct_index ? acc + 1 : acc;
  }, 0);

  if (isCompleted) {
    return (
      <QuizResultsView
        score={score}
        totalQuestions={totalQuestions}
        onRestart={handleRestart}
      />
    );
  }

  return (
    <QuizQuestionView
      question={currentQ}
      currentIndex={currentIndex}
      totalQuestions={totalQuestions}
      answeredCount={answeredCount}
      selectedOptionIndex={selectedOptionIndex}
      onSelectOption={handleSelectOption}
      onNext={handleNext}
      onPrevious={handlePrevious}
      onRestart={handleRestart}
      onSeek={onSeek}
    />
  );
};
