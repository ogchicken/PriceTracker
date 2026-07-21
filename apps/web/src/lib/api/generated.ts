/**
 * Server-only API adapter over the generated FastAPI OpenAPI types.
 * Do not import this module from client components.
 */

import "server-only";

import type { components } from "@/lib/api/contract";

export type ApiProduct = components["schemas"]["ProductResponse"];
export type ApiWatch = components["schemas"]["WatchResponse"];
export type ApiPriceObservation = components["schemas"]["PriceObservationResponse"];
export type ApiNotification = components["schemas"]["NotificationResponse"];
export type ApiPreferences = components["schemas"]["UserPreferencesResponse"];
export type ApiCreateWatch = components["schemas"]["WatchCreate"];
export type ApiUpdateWatch = components["schemas"]["WatchUpdate"];

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly details?: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export class PriceTrackerApi {
  constructor(
    private readonly baseUrl: string,
    private readonly accessToken?: string
  ) {}

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const response = await fetch(`${this.baseUrl.replace(/\/$/, "")}${path}`, {
      ...init,
      signal: init.signal ?? AbortSignal.timeout(8_000),
      headers: {
        Accept: "application/json",
        ...(init.body ? { "Content-Type": "application/json" } : {}),
        ...(this.accessToken ? { Authorization: `Bearer ${this.accessToken}` } : {}),
        ...init.headers
      }
    });

    if (!response.ok) {
      const details = await response.json().catch(() => undefined);
      throw new ApiError(`API request failed with status ${response.status}`, response.status, details);
    }

    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  }

  listWatches() {
    return this.request<ApiWatch[]>("/api/v1/watches", {
      cache: "no-store"
    });
  }

  getWatch(watchId: string) {
    return this.request<ApiWatch>(`/api/v1/watches/${encodeURIComponent(watchId)}`, {
      cache: "no-store"
    });
  }

  getHistory(watchId: string, range: "7d" | "30d" | "90d" | "all" = "all") {
    return this.request<ApiPriceObservation[]>(
      `/api/v1/watches/${encodeURIComponent(watchId)}/history?range=${range}&limit=500`,
      { cache: "no-store" }
    );
  }

  createWatch(input: ApiCreateWatch) {
    return this.request<ApiWatch>("/api/v1/watches", {
      method: "POST",
      body: JSON.stringify(input)
    });
  }

  updateWatch(watchId: string, input: ApiUpdateWatch) {
    return this.request<ApiWatch>(`/api/v1/watches/${encodeURIComponent(watchId)}`, {
      method: "PATCH",
      body: JSON.stringify(input)
    });
  }

  deleteWatch(watchId: string) {
    return this.request<void>(`/api/v1/watches/${encodeURIComponent(watchId)}`, {
      method: "DELETE"
    });
  }

  getNotifications() {
    return this.request<ApiNotification[]>("/api/v1/notifications", {
      cache: "no-store"
    });
  }

  updateNotification(notificationId: string, read: boolean) {
    return this.request<ApiNotification>(
      `/api/v1/notifications/${encodeURIComponent(notificationId)}`,
      { method: "PATCH", body: JSON.stringify({ read }) }
    );
  }

  getPreferences() {
    return this.request<ApiPreferences>("/api/v1/me/preferences", {
      cache: "no-store"
    });
  }

  savePreferences(input: Partial<Pick<ApiPreferences, "email_enabled" | "alert_rearm_percent">>) {
    return this.request<ApiPreferences>("/api/v1/me/preferences", {
      method: "PATCH",
      body: JSON.stringify(input)
    });
  }
}
