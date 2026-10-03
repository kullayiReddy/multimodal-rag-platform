import React from 'react';
import { 
  Layers, 
  MessageSquare, 
  FileText, 
  Cpu, 
  BarChart3, 
  Settings, 
  Sparkles,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';

export default function Header({ activeTab, setActiveTab, healthStatus, onUploadClick }) {
  const isHealthy = healthStatus?.status === 'healthy' || healthStatus?.status === 'demo_mode';

  return (
    <header className="navbar">
      <div className="brand-section">
        <div className="brand-icon-wrapper">
          <Layers size={22} color="#ffffff" />
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="brand-title">Multimodal RAG</span>
            <span className="brand-badge">Gemini 2.0</span>
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            Enterprise Document Intelligence Platform
          </div>
        </div>
      </div>

      <nav className="nav-links">
        <button 
          className={`nav-link ${activeTab === 'chat' ? 'active' : ''}`}
          onClick={() => setActiveTab('chat')}
        >
          <MessageSquare size={16} />
          <span>Multimodal Chat</span>
        </button>

        <button 
          className={`nav-link ${activeTab === 'documents' ? 'active' : ''}`}
          onClick={() => setActiveTab('documents')}
        >
          <FileText size={16} />
          <span>Documents</span>
        </button>

        <button 
          className={`nav-link ${activeTab === 'inspector' ? 'active' : ''}`}
          onClick={() => setActiveTab('inspector')}
        >
          <Cpu size={16} />
          <span>Hybrid Inspector</span>
        </button>

        <button 
          className={`nav-link ${activeTab === 'evaluation' ? 'active' : ''}`}
          onClick={() => setActiveTab('evaluation')}
        >
          <BarChart3 size={16} />
          <span>RAGAS Eval</span>
        </button>

        <button 
          className={`nav-link ${activeTab === 'settings' ? 'active' : ''}`}
          onClick={() => setActiveTab('settings')}
        >
          <Settings size={16} />
          <span>Settings</span>
        </button>
      </nav>

      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <button className="btn btn-primary btn-sm" onClick={onUploadClick}>
          <Sparkles size={14} />
          <span>Upload Document</span>
        </button>

        <div className="status-pill" title={`Backend: ${healthStatus?.status || 'Connecting...'}`}>
          <div className="status-dot" style={{ background: isHealthy ? 'var(--accent-emerald)' : 'var(--accent-amber)' }}></div>
          <span>{isHealthy ? 'System Active' : 'Connecting'}</span>
        </div>
      </div>
    </header>
  );
}
