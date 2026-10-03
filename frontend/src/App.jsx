import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import ChatView from './pages/ChatView';
import DocumentsView from './pages/DocumentsView';
import SearchInspectorView from './pages/SearchInspectorView';
import EvaluationView from './pages/EvaluationView';
import SettingsView from './pages/SettingsView';
import DocumentUploadModal from './components/DocumentUploadModal';
import { api } from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const [healthStatus, setHealthStatus] = useState(null);
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  useEffect(() => {
    const checkSystem = async () => {
      const status = await api.checkHealth();
      setHealthStatus(status);
    };
    checkSystem();
    const interval = setInterval(checkSystem, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleUploadComplete = () => {
    setRefreshTrigger(prev => prev + 1);
  };

  return (
    <div className="app-container">
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        healthStatus={healthStatus}
        onUploadClick={() => setIsUploadOpen(true)}
      />

      <main className="main-content">
        {activeTab === 'chat' && (
          <ChatView onUploadClick={() => setIsUploadOpen(true)} />
        )}

        {activeTab === 'documents' && (
          <DocumentsView 
            key={refreshTrigger} 
            onUploadClick={() => setIsUploadOpen(true)} 
          />
        )}

        {activeTab === 'inspector' && (
          <SearchInspectorView />
        )}

        {activeTab === 'evaluation' && (
          <EvaluationView />
        )}

        {activeTab === 'settings' && (
          <SettingsView />
        )}
      </main>

      <DocumentUploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUploadComplete={handleUploadComplete}
      />
    </div>
  );
}
