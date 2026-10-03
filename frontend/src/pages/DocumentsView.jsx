import React, { useState, useEffect } from 'react';
import { 
  FileText, 
  UploadCloud, 
  Trash2, 
  RefreshCw, 
  CheckCircle, 
  Clock, 
  AlertCircle, 
  Search, 
  Layers, 
  Table as TableIcon, 
  Image as ImageIcon,
  Sparkles
} from 'lucide-react';
import { api } from '../services/api';

export default function DocumentsView({ onUploadClick }) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchFilter, setSearchFilter] = useState('');

  const loadDocuments = async () => {
    setLoading(true);
    try {
      const res = await api.getDocuments();
      setDocuments(res.documents || []);
    } catch {
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  const handleDelete = async (id, e) => {
    e.stopPropagation();
    await api.deleteDocument(id);
    setDocuments(prev => prev.filter(d => d.id !== id));
  };

  const filteredDocs = documents.filter(d => 
    d.original_filename?.toLowerCase().includes(searchFilter.toLowerCase()) ||
    d.document_type?.toLowerCase().includes(searchFilter.toLowerCase())
  );

  const totalChunks = documents.reduce((acc, d) => acc + (d.chunk_count || 0), 0);
  const totalTables = documents.reduce((acc, d) => acc + (d.table_count || 0), 0);
  const totalImages = documents.reduce((acc, d) => acc + (d.image_count || 0), 0);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Top Stats Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' }}>
        <div className="glass-card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Ingested Documents</span>
            <FileText size={20} color="var(--accent-cyan)" />
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 700, marginTop: '8px', color: '#fff' }}>
            {documents.length}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--accent-emerald)', marginTop: '4px' }}>
            All documents vector-indexed
          </div>
        </div>

        <div className="glass-card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Total Chunks</span>
            <Layers size={20} color="var(--accent-indigo)" />
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 700, marginTop: '8px', color: '#fff' }}>
            {totalChunks}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            768-dim embeddings generated
          </div>
        </div>

        <div className="glass-card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Extracted Tables</span>
            <TableIcon size={20} color="var(--accent-emerald)" />
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 700, marginTop: '8px', color: '#fff' }}>
            {totalTables}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            Tabular markdown & cells
          </div>
        </div>

        <div className="glass-card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Visual Elements</span>
            <ImageIcon size={20} color="var(--accent-amber)" />
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 700, marginTop: '8px', color: '#fff' }}>
            {totalImages}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            Gemini Vision captioned
          </div>
        </div>
      </div>

      {/* Document Management Section */}
      <div className="glass-card" style={{ padding: '24px' }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '16px',
          marginBottom: '20px'
        }}>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Knowledge Base Documents</h2>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Multimodal corpora processed into semantic embeddings and sparse lexical tokens.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              background: 'rgba(255, 255, 255, 0.04)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              padding: '6px 12px'
            }}>
              <Search size={16} color="var(--text-muted)" />
              <input
                type="text"
                placeholder="Search documents..."
                value={searchFilter}
                onChange={e => setSearchFilter(e.target.value)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  outline: 'none',
                  color: 'var(--text-primary)',
                  fontSize: '0.85rem'
                }}
              />
            </div>

            <button className="btn btn-secondary btn-sm" onClick={loadDocuments}>
              <RefreshCw size={14} />
              <span>Refresh</span>
            </button>

            <button className="btn btn-primary btn-sm" onClick={onUploadClick}>
              <UploadCloud size={14} />
              <span>Upload New</span>
            </button>
          </div>
        </div>

        {/* Document Table */}
        <div className="data-table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Document Name</th>
                <th>Format</th>
                <th>Size</th>
                <th>Chunks</th>
                <th>Tables</th>
                <th>Visuals</th>
                <th>Status</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredDocs.length === 0 ? (
                <tr>
                  <td colSpan="8" style={{ textAlign: 'center', padding: '36px', color: 'var(--text-muted)' }}>
                    No documents found. Click "Upload New" to ingest documents.
                  </td>
                </tr>
              ) : (
                filteredDocs.map(doc => (
                  <tr key={doc.id}>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <div style={{
                          padding: '6px',
                          borderRadius: '6px',
                          background: 'rgba(56, 189, 248, 0.1)',
                          color: 'var(--accent-cyan)'
                        }}>
                          <FileText size={16} />
                        </div>
                        <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                          {doc.original_filename}
                        </span>
                      </div>
                    </td>
                    <td>
                      <span className="chip chip-cyan" style={{ fontSize: '0.72rem' }}>
                        {doc.document_type?.toUpperCase()}
                      </span>
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>
                      {(doc.file_size / 1024 / 1024).toFixed(2)} MB
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
                      {doc.chunk_count || 0}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
                      {doc.table_count || 0}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
                      {doc.image_count || 0}
                    </td>
                    <td>
                      <span className="chip chip-emerald" style={{ fontSize: '0.72rem' }}>
                        <CheckCircle size={10} /> INDEXED
                      </span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <button 
                        className="btn-icon" 
                        onClick={(e) => handleDelete(doc.id, e)}
                        title="Delete document"
                      >
                        <Trash2 size={14} color="var(--accent-rose)" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
