export function buildContext({ summary, recentEntries }) {
  const recent = recentEntries
    .slice(0, 3)
    .map(e => `[${e.created_at.slice(0, 10)}] ${e.title}: ${e.content.slice(0, 300)}`)
    .join('\n');

  return summary
    ? `Summary of earlier entries: ${summary}\n\nRecent entries:\n${recent}`
    : `Recent entries:\n${recent}`;
}