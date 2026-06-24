import React, { useState, useEffect } from 'react';
import { Save, Settings as SettingsIcon, Cpu, Globe, Folder, RefreshCw, Layers, Shield, Zap } from 'lucide-react';

const modelLists = {
  openai: [
    { id: 'gpt-4o', label: 'GPT-4o (Newest Omni)' },
    { id: 'gpt-4o-mini', label: 'GPT-4o-mini (Fast & Cheap)' },
    { id: 'gpt-4-turbo-preview', label: 'GPT-4 Turbo' },
    { id: 'gpt-4', label: 'GPT-4 (Standard)' },
    { id: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo' }
  ],
  anthropic: [
    { id: 'claude-3-5-sonnet-20240620', label: 'Claude 3.5 Sonnet' },
    { id: 'claude-3-opus-20240229', label: 'Claude 3 Opus' },
    { id: 'claude-3-haiku-20240307', label: 'Claude 3 Haiku' }
  ],
  gemini: [
    { id: 'gemini-1.5-pro', label: 'Gemini 1.5 Pro' },
    { id: 'gemini-1.5-flash', label: 'Gemini 1.5 Flash' },
    { id: 'gemini-pro', label: 'Gemini 1.0 Pro' }
  ],
  deepseek: [
    { id: 'deepseek-chat', label: 'DeepSeek Chat' },
    { id: 'deepseek-coder', label: 'DeepSeek Coder' }
  ],
  grok: [
    { id: 'grok-beta', label: 'Grok Beta' },
    { id: 'grok-1', label: 'Grok 1' }
  ]
};

const ModelSelect = ({ provider, value, onChange, customPlaceholder }) => {
  const list = modelLists[provider] || [];
  const isCustom = value && !list.find(m => m.id === value);
  
  return (
    <div className="form-group">
      <label>Model Selection</label>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        <select 
          value={isCustom ? 'custom' : (value || list[0]?.id)} 
          onChange={(e) => {
            if (e.target.value === 'custom') {
              onChange(''); 
            } else {
              onChange(e.target.value);
            }
          }}
          style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-color)', color: 'white', fontSize: '0.85rem' }}
        >
          {list.map(m => (
            <option key={m.id} value={m.id}>{m.label}</option>
          ))}
          <option value="custom">-- Custom Model ID --</option>
        </select>
        {(isCustom || !value) && (
          <input 
            type="text" 
            value={value} 
            onChange={(e) => onChange(e.target.value)} 
            placeholder={customPlaceholder || "Enter model ID manually..."}
            style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', background: 'rgba(255,100,0,0.05)', border: '1px solid rgba(255,100,0,0.3)', color: 'white', marginTop: '0.2rem', fontSize: '0.85rem' }}
          />
        )}
      </div>
    </div>
  );
};

const ProviderCard = ({ id, name, icon: Icon, color, activeProvider, onSelect, children }) => (
  <section className={`project-card ${activeProvider === id ? 'active-provider' : ''}`} style={{
    border: activeProvider === id ? `2px solid ${color}` : '1px solid var(--border-color)',
    transition: 'all 0.3s ease',
    height: '100%'
  }}>
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', color: color }}>
        <Icon size={20} />
        <h3 style={{ fontSize: '1.1rem' }}>{name}</h3>
      </div>
      <button 
        onClick={() => onSelect(id)}
        style={{
          padding: '0.4rem 1rem',
          borderRadius: '20px',
          background: activeProvider === id ? color : 'transparent',
          color: activeProvider === id ? 'black' : 'var(--text-muted)',
          border: `1px solid ${activeProvider === id ? color : 'var(--border-color)'}`,
          fontSize: '0.75rem',
          fontWeight: 700,
          cursor: 'pointer'
        }}
      >
        {activeProvider === id ? 'ACTIVE' : 'SELECT'}
      </button>
    </div>
    {children}
  </section>
);

const Settings = () => {
  const [settings, setSettings] = useState({
    active_llm_provider: 'ollama',
    ollama_url: 'http://localhost:11434',
    ollama_model: 'qwen2.5:7b-instruct-q4_K_M',
    ollama_keep_alive: -1,
    openai_api_key: '',
    openai_model: 'gpt-4-turbo-preview',
    anthropic_api_key: '',
    anthropic_model: 'claude-3-5-sonnet-20240620',
    deepseek_api_key: '',
    deepseek_model: 'deepseek-chat',
    grok_api_key: '',
    grok_model: 'grok-1',
    gemini_api_key: '',
    gemini_model: 'gemini-1.5-pro',
    embedding_model: 'sentence-transformers/all-MiniLM-L6-v2',
    doc_root: '/mnt/company-docs',
    index_path: '/app/index'
  });
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState(null);
  const [ollamaModels, setOllamaModels] = useState([]);
  const [isFetchingOllama, setIsFetchingOllama] = useState(false);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:8002/settings');
      if (response.ok) {
        const data = await response.json();
        setSettings(data);
      }
    } catch (error) {
      console.error('Failed to fetch settings', error);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchOllamaModels = async () => {
    if (!settings.ollama_url) return;
    setIsFetchingOllama(true);
    try {
      const response = await fetch(`http://localhost:8002/ollama/tags?url=${encodeURIComponent(settings.ollama_url)}`);
      if (response.ok) {
        const data = await response.json();
        setOllamaModels(data.map(m => m.name));
        if (data.length > 0 && !settings.ollama_model) {
          setSettings(s => ({...s, ollama_model: data[0].name}));
        }
      } else {
        setMessage({ type: 'error', text: 'Could not connect to Ollama URL' });
      }
    } catch (e) {
      setMessage({ type: 'error', text: 'Error fetching from local Ollama instance' });
    } finally {
      setIsFetchingOllama(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    setMessage(null);
    try {
      const response = await fetch('http://localhost:8002/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
      if (response.ok) {
        setMessage({ type: 'success', text: 'All provider settings saved and applied!' });
      } else {
        setMessage({ type: 'error', text: 'Failed to save settings.' });
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Connection error.' });
    } finally {
      setIsSaving(false);
    }
  };

  const handleReindex = async () => {
    setIsSaving(true);
    setMessage(null);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:8002/reindex', {
        method: 'POST',
        headers: { 
          'Authorization': `Bearer ${token}`
        }
      });
      const data = await response.json();
      if (data.status === 'success') {
        setMessage({ type: 'success', text: 'Vector index rebuilt successfully!' });
      } else {
        setMessage({ type: 'error', text: `Re-indexing failed: ${data.message || 'Unknown error'}` });
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Connection error during re-indexing.' });
    } finally {
      setIsSaving(false);
    }
  };


  if (isLoading) {
    return (
      <div className="dashboard" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
        <RefreshCw className="spin" size={32} color="var(--accent-color)" />
      </div>
    );
  }

  return (
    <div className="dashboard animate-fade-in" style={{ paddingBottom: '2rem' }}>
      <div className="dashboard-header" style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 style={{ fontSize: '2rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '0.8rem' }}>
            <SettingsIcon size={26} /> Multi-LLM Setup
          </h1>
          <p style={{ color: 'var(--text-muted)', marginTop: '0.3rem', fontSize: '0.9rem' }}>Connect diverse providers. Only the "Active" provider handles current chat queries.</p>
        </div>
        <button 
          onClick={handleSave}
          disabled={isSaving}
          className="btn-primary"
          style={{ 
            padding: '0.6rem 1.5rem', 
            borderRadius: '10px', 
            fontSize: '0.9rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.8rem',
            boxShadow: '0 10px 15px -3px rgba(99, 102, 241, 0.3)'
          }}
        >
          {isSaving ? <RefreshCw className="spin" size={20} /> : <Save size={20} />}
          {isSaving ? 'Applying...' : 'Apply Configuration'}
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
        <ProviderCard id="ollama" name="Local (Ollama)" icon={Cpu} color="var(--accent-color)" activeProvider={settings.active_llm_provider} onSelect={(id) => setSettings({...settings, active_llm_provider: id})}>
          <div className="form-group" style={{ marginBottom: '0.8rem' }}>
            <label style={{ fontSize: '0.8rem', marginBottom: '0.3rem' }}>Ollama Server URL</label>
            <input type="text" value={settings.ollama_url} onChange={(e) => setSettings({...settings, ollama_url: e.target.value})} placeholder="http://localhost:11434" style={{ padding: '0.5rem', fontSize: '0.85rem' }} />
          </div>
          <div className="form-group" style={{ marginBottom: '0' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.3rem' }}>
              <label style={{ fontSize: '0.8rem' }}>Model Name</label>
              <button 
                onClick={fetchOllamaModels} 
                disabled={isFetchingOllama}
                style={{ 
                  background: 'none', border: '1px solid var(--border-color)', borderRadius: '4px', 
                  padding: '0.1rem 0.5rem', color: 'var(--text-muted)', fontSize: '0.7rem', cursor: 'pointer',
                  display: 'flex', alignItems: 'center', gap: '0.2rem'
                }}
              >
                <RefreshCw size={10} className={isFetchingOllama ? 'spin' : ''}/> Fetch
              </button>
            </div>
            
            {ollamaModels.length > 0 ? (
              <select 
                value={settings.ollama_model} 
                onChange={(e) => setSettings({...settings, ollama_model: e.target.value})}
                style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-color)', color: 'white', fontSize: '0.85rem' }}
              >
                {ollamaModels.map(m => <option key={m} value={m}>{m}</option>)}
                <option value="custom">-- Custom Input --</option>
              </select>
            ) : null}
            
            {(ollamaModels.length === 0 || settings.ollama_model === 'custom' || (!ollamaModels.includes(settings.ollama_model) && settings.ollama_model !== '')) && (
              <input 
                type="text" 
                value={settings.ollama_model === 'custom' ? '' : settings.ollama_model} 
                onChange={(e) => setSettings({...settings, ollama_model: e.target.value})} 
                placeholder="qwen2.5" 
                style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-color)', color: 'white', marginTop: ollamaModels.length > 0 ? '0.4rem' : '0', fontSize: '0.85rem' }} 
              />
            )}
          </div>
        </ProviderCard>

        <ProviderCard id="openai" name="OpenAI" icon={Globe} color="#10a37f" activeProvider={settings.active_llm_provider} onSelect={(id) => setSettings({...settings, active_llm_provider: id})}>
          <div className="form-group" style={{ marginBottom: '0.8rem' }}>
            <label style={{ fontSize: '0.8rem', marginBottom: '0.3rem' }}>API Key</label>
            <input type="password" value={settings.openai_api_key} onChange={(e) => setSettings({...settings, openai_api_key: e.target.value})} placeholder="sk-..." style={{ padding: '0.5rem', fontSize: '0.85rem' }} />
          </div>
          <ModelSelect 
            provider="openai" 
            value={settings.openai_model} 
            onChange={(val) => setSettings({...settings, openai_model: val})} 
          />
        </ProviderCard>

        <ProviderCard id="anthropic" name="Anthropic" icon={Zap} color="#da7756" activeProvider={settings.active_llm_provider} onSelect={(id) => setSettings({...settings, active_llm_provider: id})}>
          <div className="form-group" style={{ marginBottom: '0.8rem' }}>
            <label style={{ fontSize: '0.8rem', marginBottom: '0.3rem' }}>API Key</label>
            <input type="password" value={settings.anthropic_api_key} onChange={(e) => setSettings({...settings, anthropic_api_key: e.target.value})} placeholder="x-ant-..." style={{ padding: '0.5rem', fontSize: '0.85rem' }} />
          </div>
          <ModelSelect 
            provider="anthropic" 
            value={settings.anthropic_model} 
            onChange={(val) => setSettings({...settings, anthropic_model: val})} 
          />
        </ProviderCard>

        <ProviderCard id="gemini" name="Gemini" icon={Layers} color="#4285f4" activeProvider={settings.active_llm_provider} onSelect={(id) => setSettings({...settings, active_llm_provider: id})}>
          <div className="form-group" style={{ marginBottom: '0.8rem' }}>
            <label style={{ fontSize: '0.8rem', marginBottom: '0.3rem' }}>API Key</label>
            <input type="password" value={settings.gemini_api_key} onChange={(e) => setSettings({...settings, gemini_api_key: e.target.value})} placeholder="AIza..." style={{ padding: '0.5rem', fontSize: '0.85rem' }} />
          </div>
          <ModelSelect 
            provider="gemini" 
            value={settings.gemini_model} 
            onChange={(val) => setSettings({...settings, gemini_model: val})} 
          />
        </ProviderCard>

        <ProviderCard id="deepseek" name="DeepSeek" icon={Shield} color="#3d5afe" activeProvider={settings.active_llm_provider} onSelect={(id) => setSettings({...settings, active_llm_provider: id})}>
          <div className="form-group" style={{ marginBottom: '0.8rem' }}>
            <label style={{ fontSize: '0.8rem', marginBottom: '0.3rem' }}>API Key</label>
            <input type="password" value={settings.deepseek_api_key} onChange={(e) => setSettings({...settings, deepseek_api_key: e.target.value})} placeholder="ds-..." style={{ padding: '0.5rem', fontSize: '0.85rem' }} />
          </div>
          <ModelSelect 
            provider="deepseek" 
            value={settings.deepseek_model} 
            onChange={(val) => setSettings({...settings, deepseek_model: val})} 
          />
        </ProviderCard>

        <ProviderCard id="grok" name="xAI (Grok)" icon={Zap} color="#888888" activeProvider={settings.active_llm_provider} onSelect={(id) => setSettings({...settings, active_llm_provider: id})}>
          <div className="form-group" style={{ marginBottom: '0.8rem' }}>
            <label style={{ fontSize: '0.8rem', marginBottom: '0.3rem' }}>API Key</label>
            <input type="password" value={settings.grok_api_key} onChange={(e) => setSettings({...settings, grok_api_key: e.target.value})} placeholder="xai-..." style={{ padding: '0.5rem', fontSize: '0.85rem' }} />
          </div>
          <ModelSelect 
            provider="grok" 
            value={settings.grok_model} 
            onChange={(val) => setSettings({...settings, grok_model: val})} 
          />
        </ProviderCard>
      </div>

      <section className="project-card" style={{ marginTop: '1rem', padding: '1rem 1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '1rem', color: '#f59e0b' }}>
          <Folder size={20} />
          <h3 style={{ fontSize: '1.1rem' }}>Global System Paths & RAG</h3>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
          <div className="form-group" style={{ marginBottom: '0' }}>
            <label style={{ fontSize: '0.8rem', marginBottom: '0.3rem' }}>Document Root</label>
            <input type="text" value={settings.doc_root} onChange={(e) => setSettings({...settings, doc_root: e.target.value})} style={{ padding: '0.5rem', fontSize: '0.85rem' }} />
          </div>
          <div className="form-group" style={{ marginBottom: '0' }}>
            <label style={{ fontSize: '0.8rem', marginBottom: '0.3rem' }}>Vector Index Path</label>
            <input type="text" value={settings.index_path} onChange={(e) => setSettings({...settings, index_path: e.target.value})} style={{ padding: '0.5rem', fontSize: '0.85rem' }} />
          </div>
          <div className="form-group" style={{ marginBottom: '0' }}>
            <label style={{ fontSize: '0.8rem', marginBottom: '0.3rem' }}>Embedding Model</label>
            <input type="text" value={settings.embedding_model} onChange={(e) => setSettings({...settings, embedding_model: e.target.value})} style={{ padding: '0.5rem', fontSize: '0.85rem' }} />
          </div>
        </div>
        <div style={{ marginTop: '1rem', display: 'flex', justifyContent: 'flex-end' }}>
          <button 
            onClick={handleReindex}
            disabled={isSaving}
            className="btn-secondary"
            style={{ 
              background: 'rgba(245, 158, 11, 0.1)', 
              color: '#f59e0b', 
              border: '1px solid rgba(245, 158, 11, 0.3)',
              padding: '0.6rem 1.2rem',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              gap: '0.6rem',
              cursor: 'pointer'
            }}
          >
            <RefreshCw size={18} className={isSaving ? 'spin' : ''} />
            Re-index Documents
          </button>
        </div>
      </section>

      {message && (
        <div className={`message ${message.type}`} style={{ marginTop: '2rem', padding: '1rem', borderRadius: '12px', textAlign: 'center' }}>
          {message.text}
        </div>
      )}

    </div>
  );
};

export default Settings;
