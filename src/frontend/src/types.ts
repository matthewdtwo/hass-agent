export interface ModelInfo {
  id: string;
  provider: string;
  name: string;
}

export type WSEventType =
  | "token"
  | "tool_call"
  | "tool_result"
  | "done"
  | "error";

export interface WSEvent {
  type: WSEventType;
  content?: string;
  name?: string;
  args?: Record<string, unknown>;
}

export interface ToolCall {
  name: string;
  args: Record<string, unknown>;
  result?: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  toolCalls?: ToolCall[];
}
