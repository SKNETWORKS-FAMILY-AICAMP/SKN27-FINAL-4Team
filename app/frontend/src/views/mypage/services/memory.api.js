import {
  MEMORY_API_ROUTES,
} from "../config/memory.constants";

function endpointWithQuery(endpoint, query) {
  return query ? `${endpoint}?${query}` : endpoint;
}

async function requestFirstAvailable(
  createRequest,
  unavailableMessage,
  responseErrorMessage,
) {
  let lastError = null;

  for (const endpoint of MEMORY_API_ROUTES) {
    try {
      const response = await createRequest(endpoint);
      if (!response.ok) {
        lastError = new Error(`${responseErrorMessage}: ${response.status}`);
        continue;
      }
      return response;
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError || new Error(unavailableMessage);
}

export async function fetchMemoryVault(force = false) {
  const query = force ? "force=true" : "";
  const response = await requestFirstAvailable(
    (endpoint) => fetch(endpointWithQuery(endpoint, query), {
      cache: "no-store",
      credentials: "include",
    }),
    "Memory API is not reachable",
    "Failed to fetch memories",
  );
  return response.json();
}

export async function deleteMemoryVaultItem(memoryId) {
  const encodedId = encodeURIComponent(memoryId);
  const response = await requestFirstAvailable(
    (endpoint) => fetch(`${endpoint}${encodedId}/`, {
      method: "DELETE",
      credentials: "include",
    }),
    "Memory delete API is not reachable",
    "Failed to delete memory",
  );

  if (response.status === 204) return {};
  return response.json().catch(() => ({}));
}
