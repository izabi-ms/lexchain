const DEFAULT_API_BASE_URL = "http://localhost:8000";
export const API_BASE_URL = (process.env.REACT_APP_BACKEND_URL || DEFAULT_API_BASE_URL).replace(/\/$/, "");

function normalizeUrl(input) {
  if (!input || input.startsWith("undefined/") || input.startsWith("null/")) {
    return `${API_BASE_URL}/${(input || "").replace(/^(undefined|null)?\/?/, "")}`;
  }
  if (input.startsWith("/")) return `${API_BASE_URL}${input}`;
  return input;
}

async function request(method, inputUrl, data, options = {}) {
  let url = normalizeUrl(inputUrl);
  if (options.params) {
    const parsed = new URL(url, window.location.origin);
    Object.entries(options.params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") parsed.searchParams.set(key, String(value));
    });
    url = parsed.toString();
  }

  const headers = { ...(options.headers || {}) };
  const requestOptions = { method, headers };
  if (data !== undefined && data !== null) {
    if (typeof FormData !== "undefined" && data instanceof FormData) {
      requestOptions.body = data;
      delete requestOptions.headers["Content-Type"];
      delete requestOptions.headers["content-type"];
    } else {
      requestOptions.body = JSON.stringify(data);
      requestOptions.headers["Content-Type"] = "application/json";
    }
  }

  let response;
  try {
    response = await fetch(url, requestOptions);
  } catch (cause) {
    const error = new Error("Network request failed. Check the backend URL and connection.");
    error.cause = cause;
    throw error;
  }

  let responseData;
  if (options.responseType === "blob") responseData = await response.blob();
  else if (options.responseType === "arraybuffer") responseData = await response.arrayBuffer();
  else if (response.status === 204) responseData = null;
  else {
    const raw = await response.text();
    if (!raw) responseData = null;
    else {
      try { responseData = JSON.parse(raw); }
      catch { responseData = raw; }
    }
  }

  if (!response.ok) {
    const error = new Error(
      typeof responseData === "object" && responseData?.detail
        ? (typeof responseData.detail === "string" ? responseData.detail : "Request validation failed.")
        : `Request failed with status ${response.status}.`
    );
    error.response = { status: response.status, data: responseData };
    throw error;
  }
  return { data: responseData, status: response.status, headers: response.headers };
}

const api = {
  get: (url, options) => request("GET", url, undefined, options),
  post: (url, data, options) => request("POST", url, data, options),
  delete: (url, options) => request("DELETE", url, undefined, options),
};

export default api;
