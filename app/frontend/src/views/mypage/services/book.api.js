export async function fetchBookRecommendation(force = false, theme = null) {
  const params = [];
  if (force) params.push("force=true");
  if (theme) params.push(`theme=${encodeURIComponent(theme)}`);
  const queryParams = params.length ? `?${params.join("&")}` : "";

  const response = await fetch(`/api/mybook/recommendation/${queryParams}`, {
    cache: "no-store",
    credentials: "include"
  });
  if (!response.ok) {
    let detail = `Failed to fetch book recommendation: ${response.status}`;
    try {
      const data = await response.json();
      detail = data.detail || data.error || detail;
    } catch (error) {
      // The status code remains useful when an upstream proxy returns non-JSON.
    }
    throw new Error(detail);
  }
  return response.json();
}
