import { API_BASE_URL } from "../api";
import { useState } from "react";

export function useStreamedGeneration() {
  const [streamedText, setStreamedText] = useState("");
  const [loading, setLoading] = useState(false);

  const generateStream = async ({ template_id, fields }) => {
    setLoading(true);
    setStreamedText("");
    const response = await fetch(`${API_BASE_URL}/generate/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ template_id, fields }),
    });
    if (!response.body) {
      setLoading(false);
      return;
    }
    const reader = response.body.getReader();
    let decoder = new TextDecoder();
    let result = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      result += chunk;
      setStreamedText((prev) => prev + chunk);
    }
    setLoading(false);
  };

  return { streamedText, loading, generateStream };
}
