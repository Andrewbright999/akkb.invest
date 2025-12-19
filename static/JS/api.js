export function getToken() {
  return localStorage.getItem("access_token");
}

export async function apiFetch(url, options = {}) {
  const headers = options.headers || {};
  return fetch(url, { ...options, headers });
}

export async function authFetch(url, options = {}) {
  const token = getToken();
  const headers = { ...(options.headers || {}) };

  if (token) headers.Authorization = `Bearer ${token}`;
  return fetch(url, { ...options, headers });
}
