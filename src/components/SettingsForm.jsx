import { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';

export default function SettingsForm() {
  const [provider, setProvider] = useState('claude');
  const [apiKey, setApiKey] = useState('');
  const [model, setModel] = useState('claude-sonnet-4-6');
  const [maxTokens, setMaxTokens] = useState(300);

  useEffect(() => {
    // Load from localStorage — keeps the key off the server entirely
    const saved = JSON.parse(localStorage.getItem('llm_settings') || '{}');
    if (saved.provider) setProvider(saved.provider);
    if (saved.apiKey) setApiKey(saved.apiKey);
    if (saved.model) setModel(saved.model);
    if (saved.maxTokens) setMaxTokens(saved.maxTokens);
  }, []);

  function save() {
    localStorage.setItem('llm_settings', JSON.stringify({ provider, apiKey, model, maxTokens }));
    alert('Settings saved locally in this browser.');
  }

  return (
    <div className="p-4 max-w-md flex flex-col gap-3">
      <h2 className="text-lg font-semibold">LLM Settings</h2>

      <label className="text-sm font-medium">Provider</label>
      <select value={provider} onChange={e => setProvider(e.target.value)} className="border rounded p-2">
        <option value="claude">Claude (Anthropic)</option>
        <option value="gemini">Gemini (Google)</option>
      </select>

      <label className="text-sm font-medium">API Key</label>
      <input
        type="password"
        className="border rounded p-2"
        value={apiKey}
        onChange={e => setApiKey(e.target.value)}
        placeholder="sk-ant-... or AIza..."
      />

      <label className="text-sm font-medium">Model</label>
      <input
        className="border rounded p-2"
        value={model}
        onChange={e => setModel(e.target.value)}
      />

      <label className="text-sm font-medium">Max reply tokens</label>
      <input
        type="number"
        className="border rounded p-2"
        value={maxTokens}
        onChange={e => setMaxTokens(Number(e.target.value))}
      />

      <button onClick={save} className="bg-black text-white px-4 py-2 rounded self-start">
        Save Settings
      </button>
      <p className="text-xs text-gray-500">
        Your API key is stored only in this browser's local storage — it is never sent to our database.
      </p>
    </div>
  );
}