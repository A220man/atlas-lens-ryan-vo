import {
  AuditLogEntry,
  ChatDetailResponse,
  ChatRecord,
  EvaluationMetricSummary,
  McpServerResponse,
  McpToolExecuteResponse,
  PromptHygieneResponse,
  PromptMessageItem,
  RoleType,
  TokenResponse,
  User,
  UserMcpHeaderResponse,
} from './types';

class ApiClient {
  private token: string | null = null;
  private baseUrl: string = '/api';

  setToken(token: string | null) {
    this.token = token;
  }

  getToken(): string | null {
    return this.token;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
      try {
        const errorJson = await response.json();
        if (errorJson.detail) {
          errorMessage = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail);
        }
      } catch {
        // Fallback to text status
      }
      throw new Error(errorMessage);
    }

    return response.json();
  }

  // Health
  async getHealth() {
    return this.request<{ status: string; app: string; version: string; env: string }>('/health');
  }

  // Auth
  async demoLogin(role: RoleType, email: string = 'developer@atlas-lens.local'): Promise<TokenResponse> {
    return this.request<TokenResponse>('/auth/demo-login', {
      method: 'POST',
      body: JSON.stringify({ role, email }),
    });
  }

  async getMe(): Promise<User> {
    return this.request<User>('/auth/me');
  }

  async logout(): Promise<void> {
    await this.request('/auth/logout', { method: 'POST' });
    this.token = null;
  }

  // Chats
  async listChats(): Promise<ChatRecord[]> {
    return this.request<ChatRecord[]>('/chats');
  }

  async getChat(chatId: string): Promise<ChatDetailResponse> {
    return this.request<ChatDetailResponse>(`/chats/${chatId}`);
  }

  async importChat(payload: any, autoRepair: boolean = true): Promise<any> {
    return this.request(`/chats/import?auto_repair=${autoRepair}`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async repairChat(chatId: string): Promise<any> {
    return this.request(`/chats/${chatId}/repair`, {
      method: 'POST',
    });
  }

  async deleteChat(chatId: string): Promise<void> {
    await this.request(`/chats/${chatId}`, { method: 'DELETE' });
  }

  // Prompt Hygiene
  async inspectHygiene(
    messages: PromptMessageItem[],
    reinjectReasoning: boolean = false,
    modelId: string = 'default'
  ): Promise<PromptHygieneResponse> {
    return this.request<PromptHygieneResponse>('/hygiene/inspect', {
      method: 'POST',
      body: JSON.stringify({
        model_id: modelId,
        reinject_reasoning: reinjectReasoning,
        messages,
      }),
    });
  }

  // MCP Servers & Headers
  async listMcpServers(): Promise<McpServerResponse[]> {
    return this.request<McpServerResponse[]>('/mcp/servers');
  }

  async registerMcpServer(name: string, url: string, description: string = ''): Promise<McpServerResponse> {
    return this.request<McpServerResponse>('/mcp/servers', {
      method: 'POST',
      body: JSON.stringify({ name, url, description }),
    });
  }

  async getUserMcpHeaders(serverId: string): Promise<UserMcpHeaderResponse[]> {
    return this.request<UserMcpHeaderResponse[]>(`/mcp/servers/${serverId}/headers`);
  }

  async setUserMcpHeader(serverId: string, headerKey: string, headerValue: string): Promise<UserMcpHeaderResponse> {
    return this.request<UserMcpHeaderResponse>(`/mcp/servers/${serverId}/headers`, {
      method: 'POST',
      body: JSON.stringify({ header_key: headerKey, header_value: headerValue }),
    });
  }

  async executeMcpTool(serverId: string, toolName: string, args: Record<string, any> = {}): Promise<McpToolExecuteResponse> {
    return this.request<McpToolExecuteResponse>('/mcp/execute', {
      method: 'POST',
      body: JSON.stringify({ server_id: serverId, tool_name: toolName, arguments: args }),
    });
  }

  // Evaluations
  async runEvaluation(sampleCount: number = 20): Promise<EvaluationMetricSummary> {
    return this.request<EvaluationMetricSummary>('/evaluations/run', {
      method: 'POST',
      body: JSON.stringify({ sample_count: sampleCount }),
    });
  }

  async listEvaluations(): Promise<any[]> {
    return this.request<any[]>('/evaluations');
  }

  // Audit
  async getAuditLogs(limit: number = 50): Promise<AuditLogEntry[]> {
    return this.request<AuditLogEntry[]>(`/audit/logs?limit=${limit}`);
  }
}

export const api = new ApiClient();
