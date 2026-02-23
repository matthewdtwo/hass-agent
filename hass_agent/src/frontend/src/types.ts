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
  | "error"
  | "session_created";

export interface WSEvent {
  type: WSEventType;
  content?: string;
  name?: string;
  args?: Record<string, unknown>;
  session_id?: string;
  title?: string;
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

export interface SessionInfo {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface DisplayMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  tool_calls?: ToolCall[];
  created_at: string;
}
