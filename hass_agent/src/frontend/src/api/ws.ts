import { useCallback, useRef, useState } from "react";
import type { ChatMessage, ToolCall, TokenUsage, WSEvent } from "../types";

interface UseAgentChatOptions {
  sessionId: string | null;
  onSessionCreated?: (sessionId: string, title: string) => void;
}

export function useAgentChat({
  sessionId,
  onSessionCreated,
}: UseAgentChatOptions) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [tokenUsage, setTokenUsage] = useState<TokenUsage | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const pendingToolCalls = useRef<ToolCall[]>([]);
  const onSessionCreatedRef = useRef(onSessionCreated);
  onSessionCreatedRef.current = onSessionCreated;

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    // Use the current page's path as the base so the WS URL works correctly
    // whether served directly or behind HA Ingress (which prefixes the path).
    const basePath = window.location.pathname.replace(/\/$/, "");
    const base = `${protocol}//${window.location.host}${basePath}/ws/chat`;
    const url = sessionId ? `${base}?session_id=${sessionId}` : base;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onclose = () => {
      wsRef.current = null;
    };
  }, [sessionId]);

  const loadMessages = useCallback((msgs: ChatMessage[]) => {
    setMessages(msgs);
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
          case "session_created":
            onSessionCreatedRef.current?.(data.session_id!, data.title!);
            break;

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

          case "context_summary":
            // Insert summary card before the streaming assistant message
            setMessages((prev) => {
              const last = prev[prev.length - 1];
              if (last?.role === "assistant") {
                return [
                  ...prev.slice(0, -1),
                  { role: "context_summary", content: data.content ?? "" },
                  last,
                ];
              }
              return [...prev, { role: "context_summary", content: data.content ?? "" }];
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

          case "usage":
            setTokenUsage({
              input_tokens: data.input_tokens ?? 0,
              output_tokens: data.output_tokens ?? 0,
              context_tokens: data.context_tokens ?? 0,
            });
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

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
  }, []);

  return {
    messages,
    isStreaming,
    tokenUsage,
    setTokenUsage,
    sendMessage,
    connect,
    disconnect,
    loadMessages,
  };
}
