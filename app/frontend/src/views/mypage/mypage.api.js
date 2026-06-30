export async function fetchMbtiDemoPayload() {
  const endpoints = [
    "/api/mbti/monthly-demo/",
    "http://localhost:8000/api/mbti/monthly-demo/"
  ];

  let lastError = null;
  for (const endpoint of endpoints) {
    try {
      const response = await fetch(endpoint, { cache: "no-store" });
      if (!response.ok) {
        lastError = new Error(`MBTI demo API failed: ${response.status}`);
        continue;
      }
      return response.json();
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError || new Error("MBTI demo API is not reachable");
}
