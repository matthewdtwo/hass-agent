import { useEffect } from "react";
import { useAgentChat } from "../api/ws";
import ChatInput from "./ChatInput";
import MessageList from "./MessageList";

interface Props {
  model: string;
}

export default function Chat({ model }: Props) {
  const { messages, isStreaming, sendMessage, connect, clearMessages } =
    useAgentChat();

  useEffect(() => {
    connect();
  }, [connect]);

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
