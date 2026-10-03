import React, { useState } from 'react';
import { Settings, Save, CheckCircle2, Shield, Database, Cpu, Sliders } from 'lucide-react';

export default function SettingsView() {
  const [model, setModel] = useState('gemini-2.0-flash');
  const [embeddingModel, setEmbeddingModel] = useState('models/text-embedding-004');
  const [vectorStore, setVectorStore] = useState('chroma');
  const [temperature, setTemperature] = useState(0.1);
  const [topK, setTopK] = useState(10);
  const [rerankK, setRerankK] = useState(5);
  const [securityFilter, setSecurityFilter] = useState(true);
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', maxWidth: '880px', margin: '0 auto' }}>
      <div className="glass-card" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
          <Settings size={22} color="var(--accent-cyan)" />
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>System & Hyperparameter Configuration</h2>
        </div>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
          Configure foundation model providers, vector indexing, retrieval depth, and security guardrails.
        </p>

        {/* Form Sections */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', marginTop: '24px' }}>
          {/* Section: AI Models */}
          <div>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--accent-cyan)', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Cpu size={16} /> Foundation Models
            </h3>
            
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '16px' }}>
              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
                  Multimodal LLM
                </label>
                <select
                  value={model}
                  onChange={e => setModel(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    borderRadius: 'var(--radius-md)',
                    background: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid var(--border-subtle)',
                    color: 'var(--text-primary)',
                    fontFamily: 'var(--font-sans)',
                    fontSize: '0.85rem'
                  }}
                >
                  <option value="gemini-2.0-flash">Gemini 2.0 Flash (Recommended - Multimodal & Fast)</option>
                  <option value="gemini-1.5-pro">Gemini 1.5 Pro (Deep Reasoning & Massive Context)</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
                  Embedding Model (768 Dimensions)
                </label>
                <select
                  value={embeddingModel}
                  onChange={e => setEmbeddingModel(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    borderRadius: 'var(--radius-md)',
                    background: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid var(--border-subtle)',
                    color: 'var(--text-primary)',
                    fontFamily: 'var(--font-sans)',
                    fontSize: '0.85rem'
                  }}
                >
                  <option value="models/text-embedding-004">Google text-embedding-004</option>
                  <option value="sentence-transformers/all-MiniLM-L6-v2">all-MiniLM-L6-v2 (Local HuggingFace)</option>
                </select>
              </div>
            </div>
          </div>

          {/* Section: Retrieval Hyperparameters */}
          <div>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--accent-indigo)', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Sliders size={16} /> Retrieval & Reranker Hyperparameters
            </h3>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '6px' }}>
                  <span>Generation Temperature</span>
                  <span style={{ fontFamily: 'var(--font-mono)' }}>{temperature}</span>
                </div>
                <input
                  type="range"
                  min="0.0"
                  max="1.0"
                  step="0.05"
                  value={temperature}
                  onChange={e => setTemperature(parseFloat(e.target.value))}
                  style={{ width: '100%', accentColor: 'var(--accent-indigo)' }}
                />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '6px' }}>
                  <span>Hybrid Retrieval Top-K</span>
                  <span style={{ fontFamily: 'var(--font-mono)' }}>{topK}</span>
                </div>
                <input
                  type="range"
                  min="5"
                  max="30"
                  step="1"
                  value={topK}
                  onChange={e => setTopK(parseInt(e.target.value))}
                  style={{ width: '100%', accentColor: 'var(--accent-indigo)' }}
                />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '6px' }}>
                  <span>Cross-Encoder Rerank Top-K</span>
                  <span style={{ fontFamily: 'var(--font-mono)' }}>{rerankK}</span>
                </div>
                <input
                  type="range"
                  min="2"
                  max="15"
                  step="1"
                  value={rerankK}
                  onChange={e => setRerankK(parseInt(e.target.value))}
                  style={{ width: '100%', accentColor: 'var(--accent-indigo)' }}
                />
              </div>
            </div>
          </div>

          {/* Section: Security */}
          <div>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--accent-emerald)', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Shield size={16} /> Security & Guardrails
            </h3>

            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '16px',
              borderRadius: 'var(--radius-md)',
              background: 'rgba(255, 255, 255, 0.02)',
              border: '1px solid var(--border-subtle)'
            }}>
              <div>
                <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>Prompt Injection & Jailbreak Filter</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Heuristic & semantic pattern detection against instruction overrides and leakage.
                </div>
              </div>
              <button
                className={`btn btn-sm ${securityFilter ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setSecurityFilter(!securityFilter)}
              >
                {securityFilter ? 'Active' : 'Disabled'}
              </button>
            </div>
          </div>

          {/* Save Button */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: '12px', marginTop: '12px' }}>
            {saved && (
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem', color: 'var(--accent-emerald)' }}>
                <CheckCircle2 size={16} /> Settings saved successfully
              </span>
            )}
            <button className="btn btn-primary" onClick={handleSave}>
              <Save size={15} />
              <span>Save Configuration</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
