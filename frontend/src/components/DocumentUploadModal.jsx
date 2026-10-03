import React, { useState, useRef } from 'react';
import { UploadCloud, File, FileText, Image as ImageIcon, CheckCircle, AlertCircle, X, Loader2 } from 'lucide-react';
import { api } from '../services/api';

export default function DocumentUploadModal({ isOpen, onClose, onUploadComplete }) {
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState('');
  const fileInputRef = useRef(null);

  if (!isOpen) return null;

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setProgress(15);
    setStatusMessage('Uploading document stream...');

    try {
      setTimeout(() => { setProgress(45); setStatusMessage('Parsing layout, text, tables, and images...'); }, 600);
      setTimeout(() => { setProgress(75); setStatusMessage('Extracting visual semantics with Gemini Vision...'); }, 1200);
      setTimeout(() => { setProgress(90); setStatusMessage('Generating 768-dim embeddings & indexing into ChromaDB...'); }, 1800);

      const res = await api.uploadDocument(file);

      setTimeout(() => {
        setProgress(100);
        setStatusMessage('Ingestion complete!');
        setTimeout(() => {
          setUploading(false);
          setFile(null);
          onUploadComplete(res);
          onClose();
        }, 600);
      }, 2300);
    } catch (err) {
      setUploading(false);
      setStatusMessage('Error uploading file');
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '580px' }}>
        <div style={{
          padding: '20px 24px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Upload Multimodal Document</h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Supports PDFs, Word Docs, PowerPoint presentations, charts, and diagrams.
            </p>
          </div>
          <button className="btn-icon" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <div style={{ padding: '24px' }}>
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            style={{
              border: `2px dashed ${isDragging ? 'var(--accent-cyan)' : 'var(--border-subtle)'}`,
              borderRadius: 'var(--radius-lg)',
              padding: '40px 20px',
              textAlign: 'center',
              cursor: 'pointer',
              background: isDragging ? 'rgba(56, 189, 248, 0.05)' : 'rgba(255, 255, 255, 0.02)',
              transition: 'all 0.2s ease',
            }}
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept=".pdf,.docx,.pptx,.png,.jpg,.jpeg,.webp,.txt"
              style={{ display: 'none' }}
            />
            <div style={{
              width: '54px',
              height: '54px',
              borderRadius: '50%',
              background: 'rgba(56, 189, 248, 0.1)',
              color: 'var(--accent-cyan)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px'
            }}>
              <UploadCloud size={28} />
            </div>

            <div style={{ fontWeight: 600, fontSize: '0.95rem', marginBottom: '6px' }}>
              {file ? file.name : 'Choose a file or drag & drop here'}
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              {file ? `${(file.size / 1024 / 1024).toFixed(2)} MB` : 'PDF, DOCX, PPTX, PNG, JPG (up to 100MB)'}
            </div>
          </div>

          {/* Supported Format Pills */}
          <div style={{ display: 'flex', justifyContent: 'center', gap: '8px', marginTop: '16px' }}>
            <span className="chip chip-cyan"><FileText size={12} /> PDF</span>
            <span className="chip chip-indigo"><File size={12} /> DOCX / PPTX</span>
            <span className="chip chip-emerald"><ImageIcon size={12} /> PNG / JPG Charts</span>
          </div>

          {/* Progress bar if uploading */}
          {uploading && (
            <div style={{ marginTop: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', marginBottom: '6px' }}>
                <span style={{ color: 'var(--accent-cyan)' }}>{statusMessage}</span>
                <span style={{ fontFamily: 'var(--font-mono)' }}>{progress}%</span>
              </div>
              <div style={{
                height: '6px',
                background: 'rgba(255, 255, 255, 0.1)',
                borderRadius: '9999px',
                overflow: 'hidden'
              }}>
                <div style={{
                  height: '100%',
                  width: `${progress}%`,
                  background: 'linear-gradient(90deg, var(--accent-cyan), var(--accent-indigo))',
                  transition: 'width 0.4s ease'
                }} />
              </div>
            </div>
          )}
        </div>

        <div style={{
          padding: '16px 24px',
          borderTop: '1px solid var(--border-subtle)',
          display: 'flex',
          justifyContent: 'flex-end',
          gap: '12px',
        }}>
          <button className="btn btn-secondary btn-sm" onClick={onClose} disabled={uploading}>
            Cancel
          </button>
          <button 
            className="btn btn-primary btn-sm" 
            onClick={handleUpload}
            disabled={!file || uploading}
          >
            {uploading ? (
              <>
                <Loader2 size={14} className="animate-spin" />
                <span>Ingesting...</span>
              </>
            ) : (
              <span>Start Ingestion Pipeline</span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
