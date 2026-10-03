import React, { useState } from 'react';
import { Cpu, Search, Sliders, ArrowRight, Zap, Filter, CheckCircle2, Layers } from 'lucide-react';

export default function SearchInspectorView() {
  const [query, setQuery] = useState("Q3 operating margin and financial breakdown");
  const [semanticWeight, setSemanticWeight] = useState(0.7);
  const [enableReranker, setEnableReranker] = useState(true);

  // High-fidelity sample retrieval candidates showing hybrid breakdown
  const candidates = [
    {
      id: "chunk-tb-01",
      document: "NovaTech_FY2024_Financial_Report.pdf",
      page: 3,
      type: "table",
      denseScore: 0.92,
      denseRank: 1,
      bm25Score: 4.85,
      bm25Rank: 2,
      rrfScore: 0.0324,
      rerankScore: 0.965,
      snippet: "Table 1: Quarterly Financial Summary (FY2024) | Q3 Revenue: $15.5M, Operating Income: $6.4M, Net Margin: 41.2% | Operating expenses: $9.1M",
    },
    {
      id: "chunk-tx-04",
      document: "NovaTech_FY2024_Financial_Report.pdf",
      page: 3,
      type: "text",
      denseScore: 0.88,
      denseRank: 2,
      bm25Score: 5.12,
      bm25Rank: 1,
      rrfScore: 0.0321,
      rerankScore: 0.912,
      snippet: "Key takeaway: Q3 2024 witnessed the highest acceleration in operating income margin at 41.2%, primarily attributed to multimodal document routing.",
    },
    {
      id: "chunk-tb-02",
      document: "NovaTech_FY2024_Financial_Report.pdf",
      page: 4,
      type: "table",
      denseScore: 0.76,
      denseRank: 4,
      bm25Score: 3.42,
      bm25Rank: 3,
      rrfScore: 0.0298,
      rerankScore: 0.840,
      snippet: "Table 2: Revenue Distribution by Product Division | Multimodal Intelligence: $26.8M (+65.4%), Active Customers: 1,420",
    },
    {
      id: "chunk-tx-01",
      document: "NovaTech_FY2024_Financial_Report.pdf",
      page: 1,
      type: "text",
      denseScore: 0.81,
      denseRank: 3,
      bm25Score: 2.10,
      bm25Rank: 5,
      rrfScore: 0.0285,
      rerankScore: 0.785,
      snippet: "Executive Summary: Consolidated revenue reached $58.4 million (+24.5% YoY). Gross profit margins expanded by 340 bps to 68.2%.",
    }
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Overview & Theory Banner */}
      <div className="glass-card" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
          <div style={{
            width: '36px',
            height: '36px',
            borderRadius: '8px',
            background: 'rgba(56, 189, 248, 0.15)',
            color: 'var(--accent-cyan)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <Cpu size={20} />
          </div>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Hybrid Retrieval & Reranking Inspector</h2>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              Inspect and debug Reciprocal Rank Fusion (RRF) between Dense Vector (768-dim) and Sparse BM25 lexical search.
            </p>
          </div>
        </div>

        {/* Controls */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '20px',
          marginTop: '20px',
          padding: '16px',
          background: 'rgba(255, 255, 255, 0.02)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border-subtle)'
        }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '8px' }}>
              <span style={{ fontWeight: 600 }}>Hybrid Balance: Dense vs Sparse</span>
              <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>
                {(semanticWeight * 100).toFixed(0)}% Vector / {((1 - semanticWeight) * 100).toFixed(0)}% BM25
              </span>
            </div>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={semanticWeight}
              onChange={e => setSemanticWeight(parseFloat(e.target.value))}
              style={{ width: '100%', accentColor: 'var(--accent-cyan)' }}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>Cross-Encoder Reranker</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                ms-marco-MiniLM-L-6-v2 deep contextual rescoring
              </div>
            </div>
            <button
              className={`btn btn-sm ${enableReranker ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setEnableReranker(!enableReranker)}
            >
              {enableReranker ? 'Enabled' : 'Disabled'}
            </button>
          </div>
        </div>
      </div>

      {/* Query Search Bar */}
      <div className="glass-card" style={{ padding: '16px 20px', display: 'flex', gap: '12px', alignItems: 'center' }}>
        <Search size={18} color="var(--accent-cyan)" />
        <input
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Test hybrid search query..."
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            outline: 'none',
            color: 'var(--text-primary)',
            fontSize: '0.95rem'
          }}
        />
        <button className="btn btn-primary btn-sm">
          <span>Run Retrieval Trace</span>
          <ArrowRight size={14} />
        </button>
      </div>

      {/* Candidate Score Breakdown Cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {candidates.map((cand, idx) => (
          <div key={cand.id} className="glass-card" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{
                  width: '28px',
                  height: '28px',
                  borderRadius: '50%',
                  background: idx === 0 ? 'linear-gradient(135deg, #38bdf8, #6366f1)' : 'rgba(255, 255, 255, 0.08)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 700,
                  fontSize: '0.85rem',
                  color: '#fff'
                }}>
                  #{idx + 1}
                </span>
                <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>{cand.document}</span>
                <span className="chip chip-cyan" style={{ fontSize: '0.7rem' }}>Page {cand.page}</span>
                <span className="chip chip-indigo" style={{ fontSize: '0.7rem' }}>{cand.type.toUpperCase()}</span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Final Rerank Score:</span>
                <span className="chip chip-emerald" style={{ fontSize: '0.82rem', fontFamily: 'var(--font-mono)' }}>
                  {(cand.rerankScore * 100).toFixed(1)}%
                </span>
              </div>
            </div>

            {/* Snippet text */}
            <div style={{
              fontSize: '0.85rem',
              color: 'var(--text-secondary)',
              background: 'rgba(0, 0, 0, 0.25)',
              padding: '12px 16px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-subtle)',
              marginBottom: '16px',
              fontFamily: 'var(--font-mono)'
            }}>
              {cand.snippet}
            </div>

            {/* Retrieval Score Meters */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                  <span>Dense Vector Similarity (Rank #{cand.denseRank})</span>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>
                    {(cand.denseScore * 100).toFixed(0)}%
                  </span>
                </div>
                <div style={{ height: '5px', background: 'rgba(255,255,255,0.08)', borderRadius: '9999px', overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: `${cand.denseScore * 100}%`, background: 'var(--accent-cyan)' }} />
                </div>
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                  <span>BM25 Sparse Score (Rank #{cand.bm25Rank})</span>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-indigo)' }}>
                    {cand.bm25Score} pts
                  </span>
                </div>
                <div style={{ height: '5px', background: 'rgba(255,255,255,0.08)', borderRadius: '9999px', overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: `${Math.min(100, (cand.bm25Score / 6) * 100)}%`, background: 'var(--accent-indigo)' }} />
                </div>
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                  <span>RRF Score (k=60 fusion)</span>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-emerald)' }}>
                    {(cand.rrfScore * 1000).toFixed(1)} m-pts
                  </span>
                </div>
                <div style={{ height: '5px', background: 'rgba(255,255,255,0.08)', borderRadius: '9999px', overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: `${(cand.rrfScore / 0.035) * 100}%`, background: 'var(--accent-emerald)' }} />
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
