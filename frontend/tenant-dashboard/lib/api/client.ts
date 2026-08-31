// Centralized API client for ModeraShield dashboard

export interface OverviewMetrics {
  total_requests: number;
  approved_requests: number;
  flagged_requests: number;
  failed_requests: number;
  flag_rate: number;
}

export interface StatusBreakdown {
  statuses: Record<string, number>;
}

export interface CategoryMetrics {
  categories: Record<string, number>;
}

export interface UsageDay {
  date: string;
  requests: number;
  approved: number;
  flagged: number;
  failed: number;
}

export interface UsageMetrics {
  days: UsageDay[];
}

export interface RecentRequestItem {
  id: string;
  content_type: string;
  status: string;
  is_flagged: boolean | null;
  categories: string[];
  model: string | null;
  created_at: string;
  updated_at: string;
}

export interface RecentRequestsResponse {
  items: RecentRequestItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface ModerationResultResponse {
  id: string;
  status: string;
  is_flagged: boolean | null;
  categories: string[];
  scores: Record<string, number>;
  model: string | null;
  created_at: string;
  updated_at: string;
  content_type?: string;
  content?: string;
}

export interface TenantResponse {
  id: string;
  name: string;
  slug: string;
  plan: string;
  status: string;
}

export interface ApiKeyCreatedResponse {
  id: string;
  name: string;
  created_at: string;
  is_active: boolean;
  key: string;
}

export interface ApiKeyResponse {
  id: string;
  name: string;
  created_at: string;
  is_active: boolean;
  last_used_at?: string | null;
}

export interface WebhookResponse {
  id: string;
  url: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
  secret?: string;
}

export interface WebhookDeliveryResponse {
  id: string;
  webhook_id: string;
  request_id: string;
  event_type: string;
  status: string;
  attempt_count: number;
  last_error: string | null;
  next_attempt_at: string | null;
  delivered_at: string | null;
  created_at: string;
  updated_at: string;
}

// Helper to get local API Key
export function getStoredApiKey(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("moderashield_api_key");
}

export function setStoredApiKey(key: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem("moderashield_api_key", key);
  }
}

export function removeStoredApiKey(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem("moderashield_api_key");
    localStorage.removeItem("moderashield_tenant_id");
    localStorage.removeItem("moderashield_tenant_name");
  }
}

export function getStoredTenant(): { id: string; name: string } | null {
  if (typeof window === "undefined") return null;
  const id = localStorage.getItem("moderashield_tenant_id");
  const name = localStorage.getItem("moderashield_tenant_name");
  if (id && name) return { id, name };
  return null;
}

export function setStoredTenant(id: string, name: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem("moderashield_tenant_id", id);
    localStorage.setItem("moderashield_tenant_name", name);
  }
}

export const apiClient = {
  getApiUrl(): string {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("moderashield_api_url");
      if (stored) return stored;
    }
    let url = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    if (!url.endsWith("/api/v1")) {
      url = `${url.replace(/\/$/, "")}/api/v1`;
    }
    return url;
  },

  async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.getApiUrl()}${path}`;
    const apiKey = getStoredApiKey();
    
    const headers = new Headers(options.headers);
    if (apiKey) {
      headers.set("X-API-Key", apiKey);
    }
    headers.set("Accept", "application/json");
    if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }

    try {
      const response = await fetch(url, { ...options, headers });
      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          removeStoredApiKey();
          if (typeof window !== "undefined") {
            window.location.href = "/login?error=session_expired"; // eslint-disable-line @next/next/no-location-assign-relative-destination
          }
        }
        let errorDetail = "API Error";
        try {
          const body = await response.json();
          errorDetail = body.detail || JSON.stringify(body);
        } catch {
          errorDetail = `HTTP error ${response.status}`;
        }
        throw new Error(errorDetail);
      }
      return await response.json() as T;
    } catch (e: any) { // eslint-disable-line @typescript-eslint/no-explicit-any
      throw e;
    }
  },

  // Check if API is available and key is valid
  async testConnection(key?: string): Promise<{ ok: boolean; message: string; tenant_id?: string; tenant_name?: string }> {
    const keyToUse = key || getStoredApiKey();
    if (!keyToUse) {
      return { ok: false, message: "No API Key provided. Set it in login/signup or settings." };
    }
    try {
      // Use zero UUID as dummy to reach get_current_tenant check, which handles actual tenant resolution
      const tenantInfo = await this.request<{ message: string; tenant_id: string; tenant_name: string }>(
        "/tenants/00000000-0000-0000-0000-000000000000/api-keys/verify-tenant",
        {
          headers: {
            "X-API-Key": keyToUse
          }
        }
      );
      return { ok: true, message: "Connected successfully", tenant_id: tenantInfo.tenant_id, tenant_name: tenantInfo.tenant_name };
    } catch (err: any) { // eslint-disable-line @typescript-eslint/no-explicit-any
      return { ok: false, message: err.message || "Failed to connect to API" };
    }
  },

  // 1. Overview Metrics
  async getOverview(): Promise<OverviewMetrics> {
    return await this.request<OverviewMetrics>("/metrics/overview");
  },

  // 2. Status Breakdown
  async getBreakdown(): Promise<StatusBreakdown> {
    return await this.request<StatusBreakdown>("/metrics/breakdown");
  },

  // 3. Category Metrics
  async getCategories(): Promise<CategoryMetrics> {
    return await this.request<CategoryMetrics>("/metrics/categories");
  },

  // 4. Usage Metrics Over Time
  async getUsage(days: number = 7): Promise<UsageMetrics> {
    return await this.request<UsageMetrics>(`/metrics/usage?days=${days}`);
  },

  // 5. Recent Requests
  async getRequests(page: number = 1, pageSize: number = 25): Promise<RecentRequestsResponse> {
    return await this.request<RecentRequestsResponse>(`/metrics/requests?page=${page}&page_size=${pageSize}`);
  },

  // 6. Request Detail
  async getRequestDetail(requestId: string): Promise<ModerationResultResponse> {
    return await this.request<ModerationResultResponse>(`/moderate/${requestId}`);
  },

  // 7. Create Moderation Request
  async createModerationRequest(content: string): Promise<{ id: string; status: string }> {
    return await this.request<{ id: string; status: string }>("/moderate/", {
      method: "POST",
      body: JSON.stringify({ content_type: "text", content })
    });
  },

  // 8. Tenants Creation (Signup)
  async createTenant(name: string, slug: string): Promise<TenantResponse> {
    return await this.request<TenantResponse>("/tenants/", {
      method: "POST",
      body: JSON.stringify({ name, slug })
    });
  },

  // 9. API Keys Creation
  async createApiKey(tenantId: string, name: string): Promise<ApiKeyCreatedResponse> {
    return await this.request<ApiKeyCreatedResponse>(`/tenants/${tenantId}/api-keys/`, {
      method: "POST",
      body: JSON.stringify({ name })
    });
  },

  // 10. List API Keys (Mocked or tenant-specific if supported)
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  async listApiKeys(_tenantId: string): Promise<ApiKeyResponse[]> {
    throw new Error("API key listing is not supported by the backend.");
  },

  // 11. Revoke API key
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  async revokeApiKey(_tenantId: string, _keyId: string): Promise<{ success: boolean }> {
    throw new Error("API key revocation is not supported by the backend.");
  },

  // 12. Webhooks
  async listWebhooks(): Promise<WebhookResponse[]> {
    return await this.request<WebhookResponse[]>("/webhooks/");
  },

  async createWebhook(url: string): Promise<WebhookResponse> {
    return await this.request<WebhookResponse>("/webhooks/", {
      method: "POST",
      body: JSON.stringify({ url })
    });
  },

  async updateWebhook(id: string, enabled: boolean): Promise<WebhookResponse> {
    return await this.request<WebhookResponse>(`/webhooks/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ enabled })
    });
  },

  async deleteWebhook(id: string): Promise<void> {
    await this.request<void>(`/webhooks/${id}`, {
      method: "DELETE"
    });
  },

  async getWebhookDeliveries(webhookId: string): Promise<WebhookDeliveryResponse[]> {
    return await this.request<WebhookDeliveryResponse[]>(`/webhooks/${webhookId}/deliveries`);
  }
};
