/**
 * The single hand-written API client - no codegen (BLUEPRINT.md §4).
 * BASE is "/api": Vite proxies in dev, same-origin in the container.
 * Every endpoint = exported TS interface + one-line arrow function.
 */

const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* non-JSON error body - keep statusText */
    }
    throw new Error(`API ${res.status}: ${detail}`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// --- Health --------------------------------------------------------------

export interface HealthStatus {
  status: string;
  services: Record<string, string>;
}

export const getHealth = () => request<HealthStatus>("/health");

// --- Items (example resource - replace per-app) --------------------------

export type ItemState = "pending" | "running" | "done" | "failed";

export interface Item {
  id: string;
  title: string;
  state: ItemState;
  detail: Record<string, unknown>;
  created_at: string | null;
  updated_at: string | null;
}

export interface ItemListResponse {
  entries: Item[];
  total: number;
  limit: number;
  offset: number;
}

export interface ItemStats {
  counts: Record<ItemState, number> & Record<string, number>;
  total: number;
}

export const listItems = (params: {
  state?: ItemState;
  q?: string;
  limit?: number;
  offset?: number;
}) => {
  const qs = new URLSearchParams();
  if (params.state) qs.set("state", params.state);
  if (params.q) qs.set("q", params.q);
  if (params.limit != null) qs.set("limit", String(params.limit));
  if (params.offset != null) qs.set("offset", String(params.offset));
  return request<ItemListResponse>(`/items?${qs.toString()}`);
};

export const getItemStats = () => request<ItemStats>("/items/stats");

export const createItem = (body: { title: string; detail?: Record<string, unknown> }) =>
  request<Item>("/items", { method: "POST", body: JSON.stringify(body) });

export const setItemState = (id: string, state: ItemState) =>
  request<Item>(`/items/${id}/state`, { method: "POST", body: JSON.stringify({ state }) });

export const deleteItem = (id: string) =>
  request<void>(`/items/${id}`, { method: "DELETE" });

// --- Profiles (example list->detail resource - replace per-app) -----------

export type ProfileStatus = "draft" | "published" | "archived";

export interface Profile {
  id: string;
  name: string;
  summary: string;
  status: ProfileStatus;
  tags: string[];
  attributes: Record<string, string>;
  created_at: string | null;
  updated_at: string | null;
}

export interface ProfileListResponse {
  entries: Profile[];
  total: number;
  limit: number;
  offset: number;
}

export interface ProfileStats {
  counts: Record<ProfileStatus, number> & Record<string, number>;
  total: number;
}

export const listProfiles = (params: {
  status?: ProfileStatus;
  q?: string;
  limit?: number;
  offset?: number;
}) => {
  const qs = new URLSearchParams();
  if (params.status) qs.set("status", params.status);
  if (params.q) qs.set("q", params.q);
  if (params.limit != null) qs.set("limit", String(params.limit));
  if (params.offset != null) qs.set("offset", String(params.offset));
  return request<ProfileListResponse>(`/profiles?${qs.toString()}`);
};

export const getProfileStats = () => request<ProfileStats>("/profiles/stats");

export const getProfile = (id: string) => request<Profile>(`/profiles/${id}`);

export const createProfile = (body: { name: string; summary?: string; tags?: string[] }) =>
  request<Profile>("/profiles", { method: "POST", body: JSON.stringify(body) });

export const updateProfile = (
  id: string,
  body: { name?: string; summary?: string; tags?: string[] },
) => request<Profile>(`/profiles/${id}`, { method: "PATCH", body: JSON.stringify(body) });

export const setProfileStatus = (id: string, status: ProfileStatus) =>
  request<Profile>(`/profiles/${id}/status`, { method: "POST", body: JSON.stringify({ status }) });

export const putProfileAttribute = (id: string, key: string, value: string) =>
  request<Profile>(`/profiles/${id}/attributes`, {
    method: "POST",
    body: JSON.stringify({ key, value }),
  });

export const deleteProfileAttribute = (id: string, key: string) =>
  request<Profile>(`/profiles/${id}/attributes/${encodeURIComponent(key)}`, {
    method: "DELETE",
  });

export const deleteProfile = (id: string) =>
  request<void>(`/profiles/${id}`, { method: "DELETE" });

// User directory (the app's own accounts)

export type UserRole = "admin" | "member" | "viewer";
export type UserStatus = "invited" | "active" | "disabled";

export interface AppUser {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  status: UserStatus;
  last_seen_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface UserListResponse {
  entries: AppUser[];
  total: number;
  limit: number;
  offset: number;
}

export interface UserStats {
  counts: Record<UserStatus, number> & Record<string, number>;
  total: number;
}

export const listUsers = (params: {
  role?: UserRole;
  status?: UserStatus;
  q?: string;
  limit?: number;
  offset?: number;
}) => {
  const qs = new URLSearchParams();
  if (params.role) qs.set("role", params.role);
  if (params.status) qs.set("status", params.status);
  if (params.q) qs.set("q", params.q);
  if (params.limit != null) qs.set("limit", String(params.limit));
  if (params.offset != null) qs.set("offset", String(params.offset));
  return request<UserListResponse>(`/users?${qs.toString()}`);
};

export const getUserStats = () => request<UserStats>("/users/stats");

export const inviteUser = (body: { name: string; email: string; role?: UserRole }) =>
  request<AppUser>("/users", { method: "POST", body: JSON.stringify(body) });

export const updateUser = (id: string, body: { name?: string; role?: UserRole }) =>
  request<AppUser>(`/users/${id}`, { method: "PATCH", body: JSON.stringify(body) });

export const setUserStatus = (id: string, status: UserStatus) =>
  request<AppUser>(`/users/${id}/status`, { method: "POST", body: JSON.stringify({ status }) });

export const deleteUser = (id: string) =>
  request<void>(`/users/${id}`, { method: "DELETE" });

export interface Me {
  user: AppUser | null;
  model: string;
  version: string;
}

export const getMe = () => request<Me>("/users/me");
