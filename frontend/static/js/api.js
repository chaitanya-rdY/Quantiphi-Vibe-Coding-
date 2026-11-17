// Thin fetch wrapper around the backend API. No business logic here.
async function request(path, options) {
  const res = await fetch(path, options);
  let body = null;
  try { body = await res.json(); } catch { /* non-JSON error */ }
  if (!res.ok) {
    const msg = (body && (body.detail?.[0]?.msg || body.detail)) || `Request failed (${res.status})`;
    throw new Error(typeof msg === "string" ? msg : "Request failed");
  }
  return body;
}

const post = (path, data) =>
  request(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });

export const api = {
  portfolio: (u, refresh = false) => request(`/api/portfolio/${encodeURIComponent(u)}?refresh=${refresh}`),
  match: (u, job_description) => post(`/api/portfolio/${encodeURIComponent(u)}/match`, { job_description }),
  lastMatch: (u) => request(`/api/portfolio/${encodeURIComponent(u)}/match`),
  chat: (u, question) => post(`/api/portfolio/${encodeURIComponent(u)}/chat`, { question }),
  bio: (u) => request(`/api/portfolio/${encodeURIComponent(u)}/bio`),
};
