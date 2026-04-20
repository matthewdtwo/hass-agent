import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import type { ChatMessage } from "../types";

interface Props {
  message: ChatMessage;
}

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm ${
          isUser
            ? "bg-blue-600 text-white"
            : "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200"
        }`}
      >
        {/* Tool calls */}
        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className="mb-2 space-y-1">
            {message.toolCalls.map((tc, i) => (
              <div
                key={i}
                className="rounded-md border border-gray-200 bg-gray-50 px-3 py-2 text-xs dark:border-gray-600 dark:bg-gray-900"
              >
                <div className="flex items-center gap-2">
                  <span className="font-mono text-yellow-400">{tc.name}</span>
                  {tc.result ? (
                    <span className="text-green-600 dark:text-green-400">done</span>
                  ) : (
                    <span className="animate-pulse text-gray-400 dark:text-gray-500">
                      running...
                    </span>
                  )}
                </div>
                {tc.args && Object.keys(tc.args).length > 0 && (
                  <div className="mt-1 text-gray-400 dark:text-gray-500">
                    {Object.entries(tc.args).map(([k, v]) => (
                      <span key={k} className="mr-2">
                        {k}={JSON.stringify(v)}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Message content */}
        {isUser ? (
          <div className="whitespace-pre-wrap">{message.content}</div>
        ) : (
          <div className="markdown-body">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeHighlight]}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}
