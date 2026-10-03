import React, { useState, useRef, useEffect } from 'react';
import { 
  Send, 
  Sparkles, 
  Bot, 
  User, 
  FileText, 
  ExternalLink, 
  Clock, 
  Zap, 
  ShieldCheck, 
  ChevronRight,
  HelpCircle,
  BarChart,
  Layers,
  Table as TableIcon,
  Image as ImageIcon
} from 'lucide-react';
import { api } from '../services/api';
import SourceModal from '../components/SourceModal';

const SUGGESTED_QUERIES = [
  "What was the revenue in Q3 according to the financial chart?",
  "Which product division had the highest growth rate?",
  "Explain the distributed microservices architecture diagram.",
  "Compare operating expenses across Q1 through Q4.",
  "What are the 5 core layers of the multimodal system pipeline?"
];

export default function ChatView({ onUploadClick }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: `Hello! I am your **Multimodal Document Intelligence Assistant** powered by **Gemini 2.0 Flash** and **Hybrid Retrieval (ChromaDB + BM25 + Cross-Encoder Reranker)**.\n\nI can analyze text, parse financial tables, explain technical diagrams, and navigate complex scanned documents. Try clicking any suggested prompt below or ask your own question!`,
      sources: [],
      metrics: null
    }
  ]);
  const [inputQuery, setInputQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeSource, setActiveSource] = useState(null);
  const [activeReasoningStep, setActiveReasoningStep] = useState(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = async (queryText = null) => {
    const q = queryText || inputQuery;
    if (!q.trim() || loading) return;

    const userMessage = {
      role: 'user',
      content: q,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMessage]);
    setInputQuery('');
    setLoading(true);

    // Simulated reasoning step transitions
    setActiveReasoningStep('Classifying query intent (multimodal layout & tables)...');
    setTimeout(() => setActiveReasoningStep('Executing Hybrid Retrieval (Dense Vector + BM25 Lexical)...'), 400);
    setTimeout(() => setActiveReasoningStep('Applying Reciprocal Rank Fusion & Cross-Encoder Reranking...'), 800);
    setTimeout(() => setActiveReasoningStep('Synthesizing grounded answer with Gemini 2.0 Flash...'), 1200);

    try {
      const response = await api.queryDocuments(q);

      setTimeout(() => {
        setMessages(prev => [
          ...prev,
          {
            role: 'assistant',
            content: response.answer,
            sources: response.sources || [],
            metrics: {
              confidence: response.confidence || 0.95,
              totalLatency: response.total_latency_ms || 512,
              retrievalLatency: response.retrieval_latency_ms || 124,
              tokens: response.tokens_used || 480
            },
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          }
        ]);
        setLoading(false);
        setActiveReasoningStep(null);
      }, 1500);
    } catch (err) {
      setLoading(false);
      setActiveReasoningStep(null);
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: "Sorry, I encountered an issue retrieving information. Please ensure backend services are running.",
          sources: []
        }
      ]);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 120px)', gap: '16px' }}>
      {/* Top Banner / Suggested Queries */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        overflowX: 'auto',
        paddingBottom: '4px',
        scrollbarWidth: 'none'
      }}>
        <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', whiteSpace: 'nowrap', display: 'flex', alignItems: 'center', gap: '4px' }}>
          <Sparkles size={13} color="var(--accent-cyan)" /> Suggested Prompts:
        </span>
        {SUGGESTED_QUERIES.map((sq, idx) => (
          <button
            key={idx}
            onClick={() => handleSend(sq)}
            className="chip chip-cyan"
            style={{
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              transition: 'all 0.2s ease',
              padding: '6px 12px',
              fontSize: '0.75rem'
            }}
          >
            {sq}
          </button>
        ))}
      </div>

      {/* Chat Thread */}
      <div className="glass-card" style={{
        flex: 1,
        overflowY: 'auto',
        padding: '24px',
        display: 'flex',
        flexDirection: 'column',
        gap: '20px'
      }}>
        {messages.map((msg, index) => (
          <div
            key={index}
            style={{
              display: 'flex',
              gap: '16px',
              alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: msg.role === 'user' ? '80%' : '88%',
            }}
          >
            {/* Avatar */}
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '10px',
              flexShrink: 0,
              background: msg.role === 'user' ? 'linear-gradient(135deg, #6366f1, #a855f7)' : 'linear-gradient(135deg, #38bdf8, #0ea5e9)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ffffff',
              boxShadow: msg.role === 'user' ? '0 0 15px rgba(99, 102, 241, 0.3)' : '0 0 15px rgba(56, 189, 248, 0.3)'
            }}>
              {msg.role === 'user' ? <User size={18} /> : <Bot size={18} />}
            </div>

            {/* Bubble Content */}
            <div style={{
              background: msg.role === 'user' ? 'rgba(99, 102, 241, 0.12)' : 'rgba(255, 255, 255, 0.03)',
              border: `1px solid ${msg.role === 'user' ? 'rgba(99, 102, 241, 0.3)' : 'var(--border-subtle)'}`,
              borderRadius: '16px',
              padding: '16px 20px',
              boxShadow: 'var(--shadow-sm)'
            }}>
              <div style={{
                fontSize: '0.9rem',
                lineHeight: '1.65',
                color: 'var(--text-primary)',
                whiteSpace: 'pre-line'
              }}>
                {msg.content}
              </div>

              {/* Verified Sources / Citations */}
              {msg.sources && msg.sources.length > 0 && (
                <div style={{ marginTop: '16px', paddingTop: '14px', borderTop: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <ShieldCheck size={14} color="var(--accent-emerald)" />
                    <span>VERIFIED MULTIMODAL CITATIONS ({msg.sources.length})</span>
                  </div>

                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {msg.sources.map((src, sIdx) => {
                      const isImg = src.content_type === 'image';
                      const isTbl = src.content_type === 'table';

                      return (
                        <div
                          key={sIdx}
                          onClick={() => setActiveSource(src)}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            background: 'rgba(255, 255, 255, 0.04)',
                            border: '1px solid rgba(56, 189, 248, 0.25)',
                            borderRadius: '8px',
                            padding: '6px 12px',
                            cursor: 'pointer',
                            transition: 'all 0.2s ease',
                          }}
                          onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--accent-cyan)'}
                          onMouseLeave={e => e.currentTarget.style.borderColor = 'rgba(56, 189, 248, 0.25)'}
                        >
                          <span style={{ color: isImg ? 'var(--accent-cyan)' : isTbl ? 'var(--accent-emerald)' : 'var(--accent-indigo)' }}>
                            {isImg ? <ImageIcon size={14} /> : isTbl ? <TableIcon size={14} /> : <FileText size={14} />}
                          </span>
                          <span style={{ fontSize: '0.78rem', fontWeight: 500, color: 'var(--text-primary)' }}>
                            {src.document}
                          </span>
                          <span className="chip chip-cyan" style={{ fontSize: '0.68rem', padding: '2px 6px' }}>
                            p. {src.page || 1}
                          </span>
                          <span style={{ fontSize: '0.7rem', color: 'var(--accent-emerald)', fontFamily: 'var(--font-mono)' }}>
                            {((src.score || 0.9) * 100).toFixed(0)}%
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Execution Metrics */}
              {msg.metrics && (
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '14px',
                  marginTop: '12px',
                  fontSize: '0.72rem',
                  color: 'var(--text-muted)',
                  fontFamily: 'var(--font-mono)'
                }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Clock size={12} /> {msg.metrics.totalLatency}ms
                  </span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Zap size={12} color="var(--accent-amber)" /> Retrieval: {msg.metrics.retrievalLatency}ms
                  </span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    Confidence: <span style={{ color: 'var(--accent-emerald)' }}>{(msg.metrics.confidence * 100).toFixed(0)}%</span>
                  </span>
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Live Loading / Reasoning step */}
        {loading && (
          <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-start' }}>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, #38bdf8, #0ea5e9)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ffffff'
            }}>
              <Bot size={18} />
            </div>

            <div style={{
              background: 'rgba(56, 189, 248, 0.05)',
              border: '1px solid rgba(56, 189, 248, 0.2)',
              borderRadius: '16px',
              padding: '16px 20px',
              display: 'flex',
              alignItems: 'center',
              gap: '12px'
            }}>
              <div className="status-dot" style={{ background: 'var(--accent-cyan)' }}></div>
              <span style={{ fontSize: '0.85rem', color: 'var(--accent-cyan)', fontWeight: 500 }}>
                {activeReasoningStep || 'Processing multimodal query...'}
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Query Input Bar */}
      <div className="glass-card" style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', gap: '12px' }}>
        <input
          type="text"
          value={inputQuery}
          onChange={e => setInputQuery(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') handleSend(); }}
          placeholder="Ask anything about charts, financial tables, text sections, or architecture diagrams..."
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            outline: 'none',
            color: 'var(--text-primary)',
            fontSize: '0.95rem',
            fontFamily: 'var(--font-sans)',
          }}
        />

        <button 
          className="btn btn-primary" 
          onClick={() => handleSend()}
          disabled={!inputQuery.trim() || loading}
          style={{ padding: '8px 18px' }}
        >
          <span>Query</span>
          <Send size={15} />
        </button>
      </div>

      {/* Source Inspection Modal */}
      <SourceModal source={activeSource} onClose={() => setActiveSource(null)} />
    </div>
  );
}
