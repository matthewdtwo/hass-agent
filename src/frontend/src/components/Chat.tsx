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

export default function Chat({ model, sessionId, onSessionCreated }: Props) {
  // Capture sessionId at mount time so mid-stream changes don't trigger a reload
  const initialSessionId = useRef(sessionId);

  const { messages, isStreaming, sendMessage, connect, loadMessages } =
    useAgentChat({ sessionId: initialSessionId.current, onSessionCreated });

  // Connect WS on mount
  useEffect(() => {
    connect();
  }, [connect]);

  // Load existing messages only when mounting with an existing session
  useEffect(() => {
    const sid = initialSessionId.current;
    if (!sid) return;
    getSessionMessages(sid).then((msgs) => {
      const chatMsgs: ChatMessage[] = msgs.map((m) => ({
        role: m.role,
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
      <ChatInput onSend={handleSend} disabled={isStreaming} />
    </div>
  );
}
