export interface ModelInfo {
  id: string;
  provider: string;
  name: string;
}

export type WSEventType =
  | "token"
  | "tool_call"
  | "tool_result"
  | "usage"
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
  // usage fields
  input_tokens?: number;
  output_tokens?: number;
  context_tokens?: number;
}

export interface TokenUsage {
  input_tokens: number;
  output_tokens: number;
  context_tokens: number;
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
