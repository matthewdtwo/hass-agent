import { useEffect, useRef } from "react";
import type { ChatMessage } from "../types";
import MessageBubble from "./MessageBubble";

interface Props {
  messages: ChatMessage[];
}

export default function MessageList({ messages }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center text-gray-400 dark:text-gray-500">
        <div className="text-center">
          <p className="text-lg font-medium">HA Maintenance Agent</p>
          <p className="mt-1 text-sm">
            Ask about your entities, devices, automations, or run maintenance
            checks.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 space-y-4 overflow-y-auto p-4">
      {messages.map((msg, i) => (
        <MessageBubble key={i} message={msg} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
