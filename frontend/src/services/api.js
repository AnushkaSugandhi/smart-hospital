export const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  (typeof window !== "undefined" && window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1"
    ? "/api/v1"
    : "http://localhost:8000/api/v1");

const TOKEN_KEY = "hospital_token";
const USER_KEY = "hospital_user";

function safeGet(key) {
  try { return localStorage.getItem(key); } catch { return null; }
}
function safeSet(key, value) {
  try { value == null ? localStorage.removeItem(key) : localStorage.setItem(key, value); } catch {}
}

export const getToken = () => safeGet(TOKEN_KEY);
export function getStoredUser() {
  try { return JSON.parse(safeGet(USER_KEY) || "null"); } catch { return null; }
}
export function clearSession() {
  safeSet(TOKEN_KEY, null);
  safeSet(USER_KEY, null);
}

let unauthorizedHandler = null;
export const onUnauthorized = (fn) => { unauthorizedHandler = fn; };

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

function authHeaders(extra = {}) {
  const token = getToken();
  return token ? { ...extra, Authorization: `Bearer ${token}` } : { ...extra };
}

export async function rawRequest(url, options = {}) {
  const response = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: authHeaders(options.headers),
  });
  if (response.status === 401 && !url.startsWith("/auth/login")) {
    clearSession();
    unauthorizedHandler?.();
  }
  if (!response.ok) {
    const text = await response.text();
    let errorMsg = text;
    try {
      const parsed = JSON.parse(text);
      errorMsg = parsed.detail || parsed.message || parsed.error || text;
    } catch {}
    throw new ApiError(errorMsg || "API request failed", response.status);
  }
  return response;
}

async function request(url, options = {}) {
  const response = await rawRequest(url, options);
  return response.json();
}

const json = (method, body) => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body ?? {}),
});

const withDept = (url, department) =>
  department ? `${url}${url.includes("?") ? "&" : "?"}department=${encodeURIComponent(department)}` : url;

export const getHealth = () => request("/health");
export const getConfig = () => request("/config");

export const getDashboardSummary = (department) => request(withDept("/dashboard/summary", department));
export const getAlerts = (includeAll = false, department) =>
  request(withDept(`/alerts${includeAll ? "?include_all=true" : ""}`, department));
export const acknowledgeAlert = (id, note) => request(`/alerts/${encodeURIComponent(id)}/acknowledge`, json("POST", { note }));
export const snoozeAlert = (id, minutes = 60) => request(`/alerts/${encodeURIComponent(id)}/snooze`, json("POST", { minutes }));

export const getHistory = (department) => request(withDept("/resources/history", department));
export const getResources = (department) => request(withDept("/resources", department));
export const getActiveDepartments = () => request("/departments/active");

export const searchHindsight = (payload = {}) => request("/hindsight/search", json("POST", payload));
export const getForecast = (metric = "admissions", horizon = 7, department) =>
  request(withDept(`/forecast?metric=${encodeURIComponent(metric)}&horizon=${horizon}`, department));
export const analyzeCascade = (payload) => request("/cascadeflow/analyze", json("POST", payload));
export const runSimulation = (payload) => request("/simulations", json("POST", payload));

export const getDecisions = () => request("/decisions");
export const recordDecision = (payload) => request("/decisions", json("POST", payload));
export const getNextActions = (department) => request(withDept("/recommendations/next", department));
export const decideNextAction = (id, decision, note) =>
  request(`/recommendations/next/${encodeURIComponent(id)}/decide`, json("POST", { decision, note }));

function fileForm(file) {
  const formData = new FormData();
  formData.append("file", file);
  return { method: "POST", body: formData };
}
export const getUploadSchema = () => request("/uploads/schema");
export const profileUpload = (file) => request("/uploads/profile", fileForm(file));
export const commitUpload = (file) => request("/uploads/commit", fileForm(file));
export const getUploadBatches = () => request("/uploads/batches");
export const getUploadBatch = (id) => request(`/uploads/batches/${id}`);
export const rollbackUploadBatch = (id) => request(`/uploads/batches/${id}/rollback`, { method: "POST" });

const query = (params) => {
  const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== "" && v != null));
  return q.toString() ? `?${q}` : "";
};
export const getAuditLog = (params = {}) => request(`/audit${query(params)}`);
export const getAuditMeta = () => request("/audit/meta");

export async function downloadFile(url, filename) {
  const response = await rawRequest(url);
  const blob = await response.blob();
  const href = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = href;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(href), 1000);
}
export const downloadTemplate = () => downloadFile("/uploads/template", "sh-dss-upload-template.csv");
export const exportAuditCsv = (params = {}) => downloadFile(`/audit/export${query(params)}`, "audit-log.csv");

export async function login(username, password) {
  const result = await request("/auth/login", json("POST", { username, password }));
  safeSet(TOKEN_KEY, result.token);
  safeSet(USER_KEY, JSON.stringify(result.user));
  return result;
}

export const getCurrentUser = () => request("/auth/me");
