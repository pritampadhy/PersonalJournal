import { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';

export default function EntryList({ onSelect, selectedId, refreshFlag }) {
  const [entries, setEntries] = useState([]);

  useEffect(() => {
    (async () => {
      const { data } = await supabase
        .from('journal_entries')
        .select('id, title, mood, created_at')
        .order('created_at', { ascending: false });
      setEntries(data || []);
    })();
  }, [refreshFlag]);

  return (
    <div className="w-64 border-r overflow-y-auto h-full">
      <ul>
        {entries.map(e => (
          <li
            key={e.id}
            onClick={() => onSelect(e.id)}
            className={`p-3 cursor-pointer border-b hover:bg-gray-50 ${
              selectedId === e.id ? 'bg-gray-100' : ''
            }`}
          >
            <div className="font-medium truncate">{e.title}</div>
            <div className="text-xs text-gray-500">
              {new Date(e.created_at).toLocaleDateString()} {e.mood && `· ${e.mood}`}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}