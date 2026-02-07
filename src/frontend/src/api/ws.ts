import { useCallback, useRef, useState } from "react";
import type { ChatMessage, ToolCall, WSEvent } from "../types";

export function useAgentChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const pendingToolCalls = useRef<ToolCall[]>([]);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/chat`);
    wsRef.current = ws;

    ws.onclose = () => {
      wsRef.current = null;
    };
  }, []);

  const sendMessage = useCallback(
    (text: string, model: string) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        connect();
        // Wait for connection then retry
        setTimeout(() => sendMessage(text, model), 500);
        return;
      }

      // Add user message
      setMessages((prev) => [...prev, { role: "user", content: text }]);
      // Add empty assistant message for streaming
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "", toolCalls: [] },
      ]);
      setIsStreaming(true);
      pendingToolCalls.current = [];

      wsRef.current.onmessage = (event) => {
        const data: WSEvent = JSON.parse(event.data);

        switch (data.type) {
          case "token":
            setMessages((prev) => {
              const last = prev[prev.length - 1];
              if (last?.role !== "assistant") return prev;
              return [
                ...prev.slice(0, -1),
                { ...last, content: last.content + (data.content ?? "") },
              ];
            });
            break;

          case "tool_call":
            pendingToolCalls.current = [
              ...pendingToolCalls.current,
              { name: data.name ?? "", args: data.args ?? {} },
            ];
            setMessages((prev) => {
              const last = prev[prev.length - 1];
              if (last?.role !== "assistant") return prev;
              return [
                ...prev.slice(0, -1),
                { ...last, toolCalls: [...pendingToolCalls.current] },
              ];
            });
            break;

          case "tool_result":
            {
              pendingToolCalls.current = pendingToolCalls.current.map((t) =>
                t.name === data.name && !t.result
                  ? { ...t, result: data.content }
                  : t
              );
              setMessages((prev) => {
                const last = prev[prev.length - 1];
                if (last?.role !== "assistant") return prev;
                return [
                  ...prev.slice(0, -1),
                  { ...last, toolCalls: [...pendingToolCalls.current] },
                ];
              });
            }
            break;

          case "done":
            setIsStreaming(false);
            break;

          case "error":
            setMessages((prev) => {
              const last = prev[prev.length - 1];
              if (last?.role !== "assistant") return prev;
              return [
                ...prev.slice(0, -1),
                {
                  ...last,
                  content: last.content + `\n\n**Error:** ${data.content}`,
                },
              ];
            });
            setIsStreaming(false);
            break;
        }
      };

      wsRef.current.send(JSON.stringify({ message: text, model }));
    },
    [connect]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    // Close and reopen WS to reset server-side history
    wsRef.current?.close();
    wsRef.current = null;
  }, []);

  return { messages, isStreaming, sendMessage, connect, clearMessages };
}
