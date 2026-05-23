import { useState } from "react";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";

interface Props {
  content: string;
}

export default function ContextSummaryCard({ content }: Props) {
  const [open, setOpen] = useState(true);

  return (
    <div className="flex justify-center my-3">
      <div className="w-full max-w-[95%] rounded-md border border-dashed border-purple-300 bg-purple-50 text-xs dark:border-purple-800 dark:bg-purple-950/30 md:max-w-[80%]">
        <button
          onClick={() => setOpen((o) => !o)}
          className="flex w-full items-center gap-2 px-3 py-2 text-left"
        >
          <svg
            className={`h-3 w-3 shrink-0 text-purple-400 transition-transform duration-150 ${open ? "rotate-90" : ""}`}
            viewBox="0 0 12 12"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M4 2l4 4-4 4" />
          </svg>
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="h-3.5 w-3.5 shrink-0 text-purple-500 dark:text-purple-400"
          >
            <path d="M10.75 16.82A7.462 7.462 0 0115 15.5c.71 0 1.396.098 2.046.282A.75.75 0 0018 15.06v-11a.75.75 0 00-.546-.721A9.006 9.006 0 0015 3a8.963 8.963 0 00-4.25 1.065V16.82zM9.25 4.065A8.963 8.963 0 005 3c-.85 0-1.673.118-2.454.339A.75.75 0 002 4.06v11a.75.75 0 00.954.721A7.506 7.506 0 015 15.5c1.579 0 3.042.487 4.25 1.32V4.065z" />
          </svg>
          <span className="font-semibold text-purple-700 dark:text-purple-300">
            System: Context summarized
          </span>
          <span className="ml-auto text-purple-400 dark:text-purple-600">
            {open ? "collapse" : "expand"}
          </span>
        </button>

        {open && (
          <div className="border-t border-dashed border-purple-200 px-3 py-2 dark:border-purple-800/50">
            <div className="markdown-body overflow-x-auto text-gray-600 dark:text-gray-400">
              <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
                {content}
              </ReactMarkdown>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
