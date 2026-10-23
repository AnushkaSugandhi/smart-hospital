const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000/api/v1";

async function request(url, options = {}) {
  const token = localStorage.getItem("hospital_token");
  const headers = { ...options.headers };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const text = await response.text();
    let errorMsg = text;
    try {
      const parsed = JSON.parse(text);
      errorMsg = parsed.detail || parsed.message || parsed.error || text;
    } catch {}
    throw new Error(errorMsg || "API request failed");
  }
  return response.json();
}

export const getHealth = () =>
  request("/health");

export const getDashboardSummary = () =>
  request("/dashboard/summary");

export const getAlerts = () =>
  request("/alerts");

export const getHistory = () =>
  request("/resources/history");

export const searchHindsight = (payload = {}) =>
  request("/hindsight/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

export const getForecast = (metric = "admissions", horizon = 7) =>
  request(`/forecast?metric=${encodeURIComponent(metric)}&horizon=${horizon}`);

export const analyzeCascade = (payload) =>
  request("/cascadeflow/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

export const runSimulation = (payload) =>
  request("/simulations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

export const getDecisions = () =>
  request("/decisions");

export const recordDecision = (payload) =>
  request("/decisions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

export const commitUpload = async (file) => {
  const formData = new FormData();
  formData.append("file", file);
  return request("/uploads/commit", {
    method: "POST",
    body: formData,
  });
};

export const login = (username, password) =>
  request("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

export const getCurrentUser = () =>
  request("/auth/me");
