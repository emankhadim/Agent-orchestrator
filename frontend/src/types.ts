
export type AgentState =
  | "intake"
  | "planning"
  | "tool_execution"
  | "validation"
  | "complete"
  | "failed";

export type ToolName = "calculator" | "knowledge_base_search" | "web_search";

export interface ToolCall {
  id: string;
  tool: ToolName;
  arguments: Record<string, unknown>;
  requested_at: string;
}

export interface ToolResult {
  call_id: string;
  tool: ToolName;
  success: boolean;
  output: string;
  error: string | null;
  completed_at: string;
}

export interface StepLog {
  step_index: number;
  from_state: AgentState;
  to_state: AgentState;
  reasoning: string;
  tool_call: ToolCall | null;
  tool_result: ToolResult | null;
  timestamp: string;
}

export type RunStatus = "running" | "complete" | "failed";

export interface RunResult {
  run_id: string;
  status: RunStatus;
  final_state: AgentState;
  answer: string | null;
  steps: StepLog[];
  created_at: string;
  finished_at: string | null;
}

export interface TaskRequest {
  query: string;
  max_steps?: number;
}
