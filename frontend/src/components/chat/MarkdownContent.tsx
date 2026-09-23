import type React from "react";
import { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Play, BookOpen } from "lucide-react";
import { parseTimeToSeconds } from "@/utils/time";

interface MarkdownContentProps {
  content: string;
  onSeek?: (seconds: number) => void;
  variant?: "chat" | "notes";
  className?: string;
}

function linkifyContent(text: string): string {
  // 1. Convert textbook citations [Class X | Book Name | Chapter Y | Page Z]
  let result = text.replace(
    /\[((?:Class\s*[^\]|]+|NCERT|Book)[^\]]*?(?:\|[^\]]+){2,})\]/gi,
    (_, citation) => `[${citation}](#cite:${encodeURIComponent(citation.trim())})`
  );

  // 2. Convert [MM:SS] or [MM:SS-MM:SS] or [MM:SS–MM:SS] into markdown links seeking to start
  result = result.replace(
    /\[(\d{1,2}:\d{2}(?::\d{2})?)(?:\s*[-–—]\s*(\d{1,2}:\d{2}(?::\d{2})?))?\]/g,
    (_, start, end) => {
      const label = end ? `${start}–${end}` : start;
      return `[${label}](#seek:${start})`;
    }
  );

  return result;
}

export const MarkdownContent: React.FC<MarkdownContentProps> = ({
  content,
  onSeek,
  variant = "chat",
  className,
}) => {
  const processed = useMemo(() => linkifyContent(content), [content]);
  const isNotes = variant === "notes";

  return (
    <div className={className}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) =>
            isNotes ? (
              <h1 className="font-serif italic text-2xl text-zinc-900 font-semibold tracking-tight pb-2.5 mb-3 border-b border-[#e5e2db] leading-snug">
                {children}
              </h1>
            ) : (
              <h1 className="text-base font-semibold text-zinc-900 mt-4 mb-2 tracking-tight">
                {children}
              </h1>
            ),
          h2: ({ children }) =>
            isNotes ? (
              <h2 className="font-semibold text-[15px] text-zinc-900 mt-5 mb-2 tracking-tight flex items-center gap-2 border-b border-[#f0eee9] pb-1">
                {children}
              </h2>
            ) : (
              <h2 className="text-[14.5px] font-semibold text-zinc-900 mt-3.5 mb-1.5 tracking-tight">
                {children}
              </h2>
            ),
          h3: ({ children }) => (
            <h3
              className={`font-semibold text-[13.5px] ${
                isNotes
                  ? "text-zinc-800 mt-3.5 mb-1"
                  : "text-zinc-900 mt-3 mb-1.5"
              } tracking-tight`}
            >
              {children}
            </h3>
          ),
          p: ({ children }) => (
            <p
              className={`my-2 text-[13.5px] ${
                isNotes ? "text-zinc-700" : "text-zinc-800"
              } leading-relaxed first:mt-0 last:mb-0`}
            >
              {children}
            </p>
          ),
          ul: ({ children }) => (
            <ul className="my-2.5 pl-4 list-disc space-y-1.5 text-[13px] text-zinc-700 marker:text-indigo-500">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="my-2.5 pl-4 list-decimal space-y-1.5 text-[13px] text-zinc-700 marker:font-mono marker:text-indigo-600 marker:text-xs">
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className="leading-relaxed pl-0.5">{children}</li>
          ),
          strong: ({ children }) => (
            <strong className="font-semibold text-zinc-900">{children}</strong>
          ),
          em: ({ children }) => (
            <em className="italic text-zinc-800">{children}</em>
          ),
          blockquote: ({ children }) => (
            <blockquote
              className={`border-l-2 border-indigo-400 bg-indigo-50/40 pl-3 py-1.5 my-2.5 rounded-r-lg ${
                isNotes ? "text-zinc-800" : "text-zinc-700 italic"
              } text-[13px] leading-relaxed`}
            >
              {children}
            </blockquote>
          ),
          hr: () => <hr className="my-4 border-[#e5e2db]" />,
          code: ({ className: codeClass, children }) => {
            const isBlock = Boolean(codeClass);
            if (isBlock) {
              return (
                <code className="font-mono text-xs block overflow-x-auto p-3 rounded-xl bg-zinc-900 text-zinc-100 border border-zinc-800 my-2.5">
                  {children}
                </code>
              );
            }
            return (
              <code className="font-mono text-[11.5px] px-1.5 py-0.5 rounded-md bg-[#f4f2ee] text-indigo-700 border border-[#e3e0d8] font-medium">
                {children}
              </code>
            );
          },
          table: ({ children }) => (
            <div className="overflow-x-auto my-2.5 rounded-xl border border-[#e5e2db]">
              <table className="w-full border-collapse text-xs text-left">
                {children}
              </table>
            </div>
          ),
          th: ({ children }) => (
            <th className="bg-[#f4f2ee] border-b border-[#e5e2db] px-3 py-1.5 font-semibold text-zinc-800">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border-b border-[#e5e2db] px-3 py-1.5 text-zinc-700 last:border-b-0">
              {children}
            </td>
          ),
          a: ({ href, children }) => {
            if (href?.startsWith("#seek:")) {
              const timeStr = href.replace("#seek:", "");
              const seconds = parseTimeToSeconds(timeStr);
              return (
                <button
                  type="button"
                  onClick={() => onSeek?.(seconds)}
                  className="inline-flex items-center gap-1 px-2.5 py-0.5 mx-1 my-0.5 rounded-full bg-indigo-50/90 hover:bg-indigo-100 text-indigo-700 hover:text-indigo-900 border border-indigo-200/90 font-mono text-[11px] font-semibold tracking-tight shadow-2xs hover:shadow-xs transition-all duration-150 cursor-pointer select-none active:scale-95 group align-baseline"
                  title={`Jump video to ${timeStr}`}
                >
                  <span className="w-3.5 h-3.5 rounded-full bg-indigo-200/60 group-hover:bg-indigo-200 flex items-center justify-center shrink-0 transition-colors">
                    <Play className="w-2 h-2 fill-current text-indigo-700 ml-0.5" />
                  </span>
                  <span className="tabular-nums">{children}</span>
                </button>
              );
            }

            if (href?.startsWith("#cite:")) {
              const rawCitation = decodeURIComponent(href.replace("#cite:", ""));
              const parts = rawCitation.split("|").map((p) => p.trim()).filter(Boolean);
              const formatted =
                parts.length >= 3
                  ? `${parts[0]} · ${parts[1]} · P. ${parts[parts.length - 1].replace(/^Page\s*/i, "")}`
                  : rawCitation;

              return (
                <span
                  className="inline-flex items-center gap-1.5 px-2.5 py-0.5 mx-1 my-0.5 rounded-full bg-amber-50/90 text-amber-900 border border-amber-200/80 text-[11px] font-medium tracking-tight shadow-2xs select-none align-baseline cursor-help"
                  title={rawCitation}
                >
                  <BookOpen className="w-3 h-3 text-amber-700 shrink-0" />
                  <span className="truncate max-w-[200px] sm:max-w-[280px]">
                    {formatted}
                  </span>
                </span>
              );
            }

            return (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-indigo-600 hover:text-indigo-800 underline underline-offset-2 font-medium"
              >
                {children}
              </a>
            );
          },
        }}
      >
        {processed}
      </ReactMarkdown>
    </div>
  );
};
