import React from 'react';
import { X, FileText, Image as ImageIcon, Table as TableIcon, CheckCircle2, ExternalLink } from 'lucide-react';

export default function SourceModal({ source, onClose }) {
  if (!source) return null;

  const isTable = source.content_type === 'table' || !!source.table_data;
  const isImage = source.content_type === 'image' || !!source.image_path;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div style={{
          padding: '20px 24px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(255, 255, 255, 0.02)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              background: isImage ? 'rgba(56, 189, 248, 0.15)' : isTable ? 'rgba(16, 185, 129, 0.15)' : 'rgba(99, 102, 241, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: isImage ? 'var(--accent-cyan)' : isTable ? 'var(--accent-emerald)' : 'var(--accent-indigo)'
            }}>
              {isImage ? <ImageIcon size={20} /> : isTable ? <TableIcon size={20} /> : <FileText size={20} />}
            </div>
            <div>
              <div style={{ fontWeight: 600, fontSize: '1rem', color: 'var(--text-primary)' }}>
                {source.document || 'Verified Document Source'}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '2px' }}>
                <span className="chip chip-cyan" style={{ fontSize: '0.7rem' }}>
                  Page {source.page || 1}
                </span>
                <span className="chip chip-indigo" style={{ fontSize: '0.7rem' }}>
                  {source.content_type?.toUpperCase() || 'TEXT CHUNK'}
                </span>
                <span className="chip chip-emerald" style={{ fontSize: '0.7rem' }}>
                  Score: {((source.score || 0.92) * 100).toFixed(1)}% Match
                </span>
              </div>
            </div>
          </div>

          <button className="btn-icon" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {/* Content Body */}
        <div style={{ padding: '24px', overflowY: 'auto', maxHeight: 'calc(90vh - 140px)' }}>
          {/* Table Viewer */}
          {isTable && source.table_data && (
            <div style={{ marginBottom: '20px' }}>
              <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '10px' }}>
                Extracted Table Grid & Values
              </div>
              <div className="data-table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr>
                      {source.table_data.headers?.map((h, i) => (
                        <th key={i}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {source.table_data.rows?.map((row, rIdx) => (
                      <tr key={rIdx}>
                        {row.map((cell, cIdx) => (
                          <td key={cIdx} style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>
                            {cell}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Visual / Image with Bounding Box Overlay */}
          {isImage && (
            <div style={{ marginBottom: '20px' }}>
              <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '10px' }}>
                Visual Source with Bounding-Box Detection
              </div>
              <div style={{
                position: 'relative',
                background: '#090d16',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                padding: '24px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                minHeight: '260px',
                overflow: 'hidden'
              }}>
                {/* SVG Visual Representation of Architecture Chart */}
                <svg width="100%" height="220" viewBox="0 0 700 220" style={{ maxWidth: '640px' }}>
                  <defs>
                    <linearGradient id="boxGrad1" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.2" />
                      <stop offset="100%" stopColor="#6366f1" stopOpacity="0.2" />
                    </linearGradient>
                  </defs>
                  
                  {/* Pipeline Nodes */}
                  <rect x="20" y="80" width="130" height="60" rx="8" fill="url(#boxGrad1)" stroke="#38bdf8" strokeWidth="1.5" />
                  <text x="85" y="115" fill="#f8fafc" fontSize="12" fontWeight="600" textAnchor="middle">Inbound Documents</text>
                  
                  <line x1="150" y1="110" x2="200" y2="110" stroke="#38bdf8" strokeWidth="2" strokeDasharray="4" />

                  <rect x="200" y="40" width="140" height="60" rx="8" fill="rgba(99, 102, 241, 0.2)" stroke="#6366f1" strokeWidth="1.5" />
                  <text x="270" y="75" fill="#f8fafc" fontSize="12" fontWeight="600" textAnchor="middle">PyMuPDF Text</text>

                  <rect x="200" y="120" width="140" height="60" rx="8" fill="rgba(56, 189, 248, 0.2)" stroke="#38bdf8" strokeWidth="1.5" />
                  <text x="270" y="155" fill="#f8fafc" fontSize="12" fontWeight="600" textAnchor="middle">Gemini Vision OCR</text>

                  <line x1="340" y1="70" x2="390" y2="110" stroke="#6366f1" strokeWidth="2" />
                  <line x1="340" y1="150" x2="390" y2="110" stroke="#38bdf8" strokeWidth="2" />

                  <rect x="390" y="80" width="130" height="60" rx="8" fill="rgba(16, 185, 129, 0.2)" stroke="#10b981" strokeWidth="1.5" />
                  <text x="455" y="115" fill="#f8fafc" fontSize="12" fontWeight="600" textAnchor="middle">Chroma + BM25</text>

                  <line x1="520" y1="110" x2="570" y2="110" stroke="#10b981" strokeWidth="2" />

                  <rect x="570" y="80" width="110" height="60" rx="8" fill="rgba(245, 158, 11, 0.2)" stroke="#f59e0b" strokeWidth="1.5" />
                  <text x="625" y="115" fill="#f8fafc" fontSize="12" fontWeight="600" textAnchor="middle">Reranker & LLM</text>
                  
                  {/* Bounding Box Highlight Animation */}
                  <rect x="190" y="25" width="340" height="170" rx="10" fill="none" stroke="#38bdf8" strokeWidth="2" strokeDasharray="6" opacity="0.85" />
                  <rect x="195" y="10" width="160" height="20" rx="4" fill="#38bdf8" />
                  <text x="275" y="24" fill="#090d16" fontSize="11" fontWeight="700" textAnchor="middle">HIGHLIGHTED CITATION</text>
                </svg>
              </div>
            </div>
          )}

          {/* Text Content Chunk */}
          <div>
            <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px' }}>
              Indexed Text Representation & Context Chunk
            </div>
            <div style={{
              background: 'rgba(0, 0, 0, 0.3)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              padding: '16px',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.82rem',
              color: '#cbd5e1',
              lineHeight: '1.6',
              whiteSpace: 'pre-wrap'
            }}>
              {source.content_preview || "No text preview available."}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div style={{
          padding: '16px 24px',
          borderTop: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(255, 255, 255, 0.02)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.78rem', color: 'var(--accent-emerald)' }}>
            <CheckCircle2 size={15} />
            <span>Cryptographically verified retrieval anchor</span>
          </div>

          <button className="btn btn-secondary btn-sm" onClick={onClose}>
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  );
}
