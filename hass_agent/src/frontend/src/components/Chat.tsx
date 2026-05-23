import { useEffect, useRef } from "react";
import { getSessionMessages } from "../api/sessions";
import { useAgentChat } from "../api/ws";
import type { ChatMessage } from "../types";
import ChatInput from "./ChatInput";
import MessageList from "./MessageList";

interface Props {
  model: string;
  sessionId: string | null;
  onSessionCreated: (id: string, title: string) => void;
}

function fmt(n: number): string {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n);
}

export default function Chat({ model, sessionId, onSessionCreated }: Props) {
  const initialSessionId = useRef(sessionId);

  const { messages, isStreaming, tokenUsage, sendMessage, connect, loadMessages } =
    useAgentChat({ sessionId: initialSessionId.current, onSessionCreated });

  useEffect(() => {
    connect();
  }, [connect]);

  useEffect(() => {
    const sid = initialSessionId.current;
    if (!sid) return;
    getSessionMessages(sid).then((msgs) => {
      const chatMsgs: ChatMessage[] = msgs.map((m) => ({
        role: m.role as ChatMessage["role"],
        content: m.content,
        toolCalls: m.tool_calls ?? undefined,
      }));
      loadMessages(chatMsgs);
    });
  }, [loadMessages]);

  const handleSend = (text: string) => {
    sendMessage(text, model);
  };

  return (
    <div className="flex h-full flex-col">
      <MessageList messages={messages} />

      {/* Token usage bar */}
      {tokenUsage && (
        <div className="flex items-center gap-4 border-t border-gray-100 px-4 py-1.5 text-xs text-gray-400 dark:border-gray-800 dark:text-gray-500">
          <span title="Current context window size">
            <span className="mr-1 font-medium text-gray-500 dark:text-gray-400">ctx</span>
            {fmt(tokenUsage.context_tokens)}
          </span>
          <span title="Total input tokens this session">
            <span className="mr-1 font-medium text-gray-500 dark:text-gray-400">in</span>
            {fmt(tokenUsage.input_tokens)}
          </span>
          <span title="Total output tokens this session">
            <span className="mr-1 font-medium text-gray-500 dark:text-gray-400">out</span>
            {fmt(tokenUsage.output_tokens)}
          </span>
        </div>
      )}

      <ChatInput onSend={handleSend} disabled={isStreaming} />
    </div>
  );
}
