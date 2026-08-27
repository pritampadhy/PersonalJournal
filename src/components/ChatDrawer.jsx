import { useState } from 'react';
import { supabase } from '../lib/supabase';
import { askClaude, askGemini } from '../lib/llm';
import { buildContext } from '../lib/context';

export default function ChatDrawer() {
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(false);

  async function ask() {
    setLoading(true);
    setAnswer('');

    const settings = JSON.parse(localStorage.getItem('llm_settings') || '{}');
    if (!settings.apiKey) {
      setAnswer('Add your API key in Settings first.');
      setLoading(false);
      return;
    }

    const { data: recentEntries } = await supabase
      .from('journal_entries')
      .select('title, content, created_at')
      .order('created_at', { ascending: false })
      .limit(3);

    const context = buildContext({ summary: null, recentEntries: recentEntries || [] });

    const fn = settings.provider === 'gemini' ? askGemini : askClaude;
    const result = await fn({
      apiKey: settings.apiKey,
      model: settings.model,
      maxTokens: settings.maxTokens,
      context,
      question
    });

    setAnswer(result);
    setLoading(false);
  }

  return (
    <div className={`fixed right-0 top-0 h-full bg-white border-l shadow-lg transition-all ${open ? 'w-96' : 'w-10'}`}>
      <button onClick={() => setOpen(!open)} className="p-2 text-sm w-full">
        {open ? '→ Close' : '💬'}
      </button>
      {open && (
        <div className="p-3 flex flex-col gap-2 h-full">
          <h3 className="font-semibold">Reflect</h3>
          <textarea
            className="border rounded p-2 text-sm"
            rows={3}
            placeholder="Ask about your journal..."
            value={question}
            onChange={e => setQuestion(e.target.value)}
          />
          <button
            onClick={ask}
            disabled={loading || !question}
            className="bg-black text-white rounded p-2 text-sm disabled:opacity-40"
          >
            {loading ? 'Thinking...' : 'Ask'}
          </button>
          <div className="text-sm mt-2 whitespace-pre-wrap overflow-y-auto flex-1">
            {answer}
          </div>
        </div>
      )}
    </div>
  );
}