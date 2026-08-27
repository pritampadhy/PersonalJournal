import { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';

export default function EntryEditor({ entryId, onSaved }) {
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [mood, setMood] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!entryId || entryId === 'new') {
      setTitle(''); setContent(''); setMood('');
      return;
    }
    (async () => {
      const { data } = await supabase
        .from('journal_entries')
        .select('*')
        .eq('id', entryId)
        .single();
      if (data) {
        setTitle(data.title);
        setContent(data.content);
        setMood(data.mood || '');
      }
    })();
  }, [entryId]);

  async function save() {
    setSaving(true);
    const { data: { user } } = await supabase.auth.getUser();

    if (entryId && entryId !== 'new') {
      await supabase
        .from('journal_entries')
        .update({ title, content, mood, updated_at: new Date().toISOString() })
        .eq('id', entryId);
    } else {
      await supabase
        .from('journal_entries')
        .insert({ title, content, mood, user_id: user.id });
    }
    setSaving(false);
    onSaved?.();
  }

  return (
    <div className="flex-1 p-4 flex flex-col gap-3">
      <input
        className="text-xl font-semibold border-b p-2 outline-none"
        placeholder="Title"
        value={title}
        onChange={e => setTitle(e.target.value)}
      />
      <input
        className="text-sm border rounded p-1 w-40"
        placeholder="Mood (optional)"
        value={mood}
        onChange={e => setMood(e.target.value)}
      />
      <textarea
        className="flex-1 border rounded p-2 outline-none resize-none"
        placeholder="Write your thoughts..."
        value={content}
        onChange={e => setContent(e.target.value)}
      />
      <button
        onClick={save}
        disabled={saving || !title || !content}
        className="self-end bg-black text-white px-4 py-2 rounded disabled:opacity-40"
      >
        {saving ? 'Saving...' : 'Save Entry'}
      </button>
    </div>
  );
}