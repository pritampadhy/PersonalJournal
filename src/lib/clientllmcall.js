// Claude call
export async function askClaude({ apiKey, model, maxTokens, context, question }) {
  const res = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": apiKey,
      "anthropic-version": "2023-06-01",
      "anthropic-dangerous-direct-browser-access": "true" // required for client-side calls
    },
    body: JSON.stringify({
      model: model || "claude-sonnet-4-6",
      max_tokens: maxTokens || 300,
      messages: [
        { role: "user", content: `Journal context:\n${context}\n\nQuestion: ${question}` }
      ]
    })
  });
  const data = await res.json();
  return data.content?.[0]?.text || "No response";
}

// Gemini call
export async function askGemini({ apiKey, model, maxTokens, context, question }) {
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${model || "gemini-2.0-flash"}:generateContent?key=${apiKey}`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      contents: [{ parts: [{ text: `Journal context:\n${context}\n\nQuestion: ${question}` }] }],
      generationConfig: { maxOutputTokens: maxTokens || 300 }
    })
  });
  const data = await res.json();
  return data.candidates?.[0]?.content?.parts?.[0]?.text || "No response";
}