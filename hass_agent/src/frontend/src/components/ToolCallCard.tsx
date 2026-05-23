import { useState } from "react";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import type { ToolCall } from "../types";

interface Props {
  tc: ToolCall;
}

function fencedJson(value: unknown): string {
  return "```json\n" + JSON.stringify(value, null, 2) + "\n```";
}

function fencedResult(raw: string): string {
  try {
    return "```json\n" + JSON.stringify(JSON.parse(raw), null, 2) + "\n```";
  } catch {
    // Not JSON — wrap as plain text code block
    return "```\n" + raw + "\n```";
  }
}

export default function ToolCallCard({ tc }: Props) {
  const [open, setOpen] = useState(false);
  const [inputOpen, setInputOpen] = useState(false);
  const [outputOpen, setOutputOpen] = useState(false);
  const hasArgs = tc.args && Object.keys(tc.args).length > 0;
  const isDone = Boolean(tc.result);

  return (
    <div className="rounded-md border border-gray-200 bg-gray-50 text-xs dark:border-gray-700 dark:bg-gray-900">
      {/* Header row — always visible, click to toggle */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left"
      >
        <svg
          className={`h-3 w-3 shrink-0 text-gray-400 transition-transform duration-150 ${open ? "rotate-90" : ""}`}
          viewBox="0 0 12 12"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M4 2l4 4-4 4" />
        </svg>

        <span className="font-mono text-yellow-500 dark:text-yellow-400">{tc.name}</span>

        {isDone ? (
          <span className="ml-1 text-green-600 dark:text-green-400">done</span>
        ) : (
          <span className="ml-1 animate-pulse text-gray-400 dark:text-gray-500">running…</span>
        )}
      </button>

      {/* Expanded detail */}
      {open && (
        <div className="border-t border-gray-200 dark:border-gray-700">
          {/* Inputs */}
          {hasArgs && (
            <div className="border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={() => setInputOpen((o) => !o)}
                className="flex w-full items-center gap-2 px-3 py-2 text-left"
              >
                <svg
                  className={`h-3 w-3 shrink-0 text-gray-400 transition-transform duration-150 ${inputOpen ? "rotate-90" : ""}`}
                  viewBox="0 0 12 12"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M4 2l4 4-4 4" />
                </svg>
                <span className="font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
                  Inputs
                </span>
              </button>
              {inputOpen && (
                <div className="px-3 pb-2">
                  <div className="markdown-body">
                    <ReactMarkdown rehypePlugins={[rehypeHighlight]}>
                      {fencedJson(tc.args)}
                    </ReactMarkdown>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Output */}
          {tc.result && (
            <div
              className={`${hasArgs ? "border-t border-gray-200 dark:border-gray-700" : ""}`}
            >
              <button
                onClick={() => setOutputOpen((o) => !o)}
                className="flex w-full items-center gap-2 px-3 py-2 text-left"
              >
                <svg
                  className={`h-3 w-3 shrink-0 text-gray-400 transition-transform duration-150 ${outputOpen ? "rotate-90" : ""}`}
                  viewBox="0 0 12 12"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M4 2l4 4-4 4" />
                </svg>
                <span className="font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
                  Output
                </span>
              </button>
              {outputOpen && (
                <div className="px-3 pb-2">
                  <div className="markdown-body max-h-[60vh] overflow-y-auto">
                    <ReactMarkdown rehypePlugins={[rehypeHighlight]}>
                      {fencedResult(tc.result)}
                    </ReactMarkdown>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
