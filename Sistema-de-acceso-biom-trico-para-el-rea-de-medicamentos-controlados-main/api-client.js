async function apiRequest(endpoint, options = {}) {
  const response = await fetch(`/api${endpoint}`, {
    ...options,
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
  });

  if (response.status === 204) return null;
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || `Error HTTP ${response.status}`);
  }
  return data;
}

window.apiRequest = apiRequest;
