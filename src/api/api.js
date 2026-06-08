
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

export const getAIMessage = async ({ messages, currentFlow }) => {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      session_id: window.localStorage.getItem("partselect_session_id") || "demo-session",
      messages,
      current_flow: currentFlow || null,
    }),
  });

  if (!response.ok) {
    throw new Error(`Backend returned ${response.status}`);
  }

  return response.json();
};
