import type React from "react";
import {
  MessageSquare,
  ListOrdered,
  HelpCircle,
  FileText,
  Layers,
} from "lucide-react";
import type { FeatureTabKey } from "@/types";

interface FeatureCardsProps {
  activeTab: FeatureTabKey;
  onSelectTab: (tab: FeatureTabKey) => void;
}

interface CardConfig {
  key: FeatureTabKey;
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
}

const CARDS: CardConfig[] = [
  {
    key: "doubt",
    title: "Doubt Solver",
    description: "Ask anything about this video",
    icon: MessageSquare,
  },
  {
    key: "chapters",
    title: "Chapters",
    description: "Jump to where the topic changes",
    icon: ListOrdered,
  },
  {
    key: "quiz",
    title: "Quiz",
    description: "Test yourself when the video ends",
    icon: HelpCircle,
  },
  {
    key: "notes",
    title: "Notes",
    description: "Key points from the lecture",
    icon: FileText,
  },
  {
    key: "flashcards",
    title: "Flashcards",
    description: "Revise the important terms",
    icon: Layers,
  },
];

export const FeatureCards: React.FC<FeatureCardsProps> = ({
  activeTab,
  onSelectTab,
}) => {
  return (
    <nav
      aria-label="Workspace feature navigation"
      className="w-full bg-[#f4f2ee] p-1 rounded-2xl border border-[#e3e0d8] flex items-center gap-1.5 shadow-xs overflow-x-auto"
    >
      {CARDS.map((card) => {
        const isSelected = activeTab === card.key;
        const IconComponent = card.icon;

        return (
          <button
            key={card.key}
            type="button"
            onClick={() => onSelectTab(card.key)}
            title={card.description}
            className={`flex-1 min-w-[110px] sm:min-w-0 h-12 px-3.5 rounded-xl flex items-center justify-center gap-2.5 transition-all duration-150 select-none cursor-pointer text-[13.5px] font-medium ${
              isSelected
                ? "bg-[#1f1f1f] text-white shadow-xs font-semibold"
                : "bg-transparent text-[#555] hover:text-[#1f1f1f] hover:bg-white/70 active:bg-white"
            }`}
          >
            <IconComponent
              className={`w-[18px] h-[18px] shrink-0 transition-colors ${
                isSelected ? "text-white" : "text-[#71717a]"
              }`}
            />
            <span className="truncate tracking-tight">{card.title}</span>
          </button>
        );
      })}
    </nav>
  );
};
