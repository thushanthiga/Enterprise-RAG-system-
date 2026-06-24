import React, { useState, useEffect } from 'react';
import { Database, FileText, Share2, ImageIcon, Plus, ArrowLeft, Trash2, ShieldCheck, Save, Server, Sparkles, Send, Eye, Settings } from 'lucide-react';
import Chat from './Chat';
import Pagination from './Pagination';

const ProjectDetails = ({ project, onBack, chats, currentChatId, setCurrentChatId, onChatUpdate, onDeleteChat }) => {
  const [activeTab, setActiveTab] = useState('chat');
  const [docs, setDocs] = useState(project.documents || []);
  const [databases, setDatabases] = useState(project.databases || []);
  const [dbConfig, setDbConfig] = useState({
    name: 'Primary DB',
    host: 'localhost',
    port: 5432,
    user: '',
    password: '',
    database: '',
    type: 'postgresql'
  });
  const [showDbForm, setShowDbForm] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [newDocName, setNewDocName] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const [projectGuidelines, setProjectGuidelines] = useState('');
  const [dbSchema, setDbSchema] = useState('');
  const [isSavingMarkdown, setIsSavingMarkdown] = useState(false);
  const [docPage, setDocPage] = useState(1);
  const [mediaPage, setMediaPage] = useState(1);
  const DOCS_PER_PAGE = 9;
  const MEDIA_PER_PAGE = 6;

  useEffect(() => {
    fetchProjectDetails();
  }, [project.id]);

  const fetchProjectDetails = async () => {
    try {
      const authToken = localStorage.getItem('token');
      const response = await fetch(`http://localhost:8002/projects/${project.id}`, {
        headers: {
          ...(authToken ? { 'Authorization': `Bearer ${authToken}` } : {})
        }
      });
      if (response.ok) {
        const data = await response.json();
        setDocs(data.documents || []);
        const dbs = data.db_config;
        if (Array.isArray(dbs)) {
          setDatabases(dbs);
        } else if (dbs && Object.keys(dbs).length > 0) {
          setDatabases([{ ...dbs, id: dbs.id || 1 }]);
        } else {
          setDatabases([]);
        }
        if (data.db_config && !showDbForm) setDbConfig(data.db_config);
      }
      
      // Fetch Markdown Contexts
      const pgRes = await fetch(`http://localhost:8002/projects/${project.id}/markdown/project_guidelines.md`, {
        headers: { ...(authToken ? { 'Authorization': `Bearer ${authToken}` } : {}) }
      });
      if(pgRes.ok) {
        setProjectGuidelines((await pgRes.json()).content);
      }
      const dbRes = await fetch(`http://localhost:8002/projects/${project.id}/markdown/db_schema.md`, {
        headers: { ...(authToken ? { 'Authorization': `Bearer ${authToken}` } : {}) }
      });
      if(dbRes.ok) {
        setDbSchema((await dbRes.json()).content);
      }
    } catch (e) {
      console.error('Failed to fetch project details', e);
    }
  };

  const [sortBy, setSortBy] = useState('date'); // 'date', 'name', 'size'

  const handleUploadDocument = async () => {
    console.log('handleUploadDocument called');
    if (!selectedFile) return;
    setIsLoading(true);
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('category', 'uploaded');

    try {
      const authToken = localStorage.getItem('token');
      const response = await fetch(`http://localhost:8002/projects/${project.id}/documents/upload?category=uploaded`, {
        method: 'POST',
        headers: {
          ...(authToken ? { 'Authorization': `Bearer ${authToken}` } : {})
        },
        body: formData,
      });
      if (response.ok) {
        const addedDoc = await response.json();
        setDocs([...docs, addedDoc]);
        setSelectedFile(null);
        document.getElementById('file-upload').value = '';
        alert('Document uploaded successfully!');
      }
    } catch (e) {
      console.error('Upload document failed', e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleUploadMedia = async () => {
    console.log('handleUploadMedia called');
    if (!selectedFile) return;
    setIsLoading(true);
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('category', 'media');

    try {
      const authToken = localStorage.getItem('token');
      const response = await fetch(`http://localhost:8002/projects/${project.id}/documents/upload?category=media`, {
        method: 'POST',
        headers: {
          ...(authToken ? { 'Authorization': `Bearer ${authToken}` } : {})
        },
        body: formData,
      });
      if (response.ok) {
        const addedMedia = await response.json();
        const updatedDocs = [...docs, addedMedia];
        setDocs(updatedDocs);
        setSelectedFile(null);
        document.getElementById('media-upload').value = '';
        alert('Media asset uploaded successfully!');
      }
    } catch (e) {
      console.error('Upload media failed', e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleViewFile = (docId) => {
    window.open(`http://localhost:8002/projects/${project.id}/files/${docId}`, '_blank');
  };

  const sortItems = (items) => {
    return [...items].sort((a, b) => {
      if (sortBy === 'name') return a.name.localeCompare(b.name);
      if (sortBy === 'date') return new Date(b.created_at) - new Date(a.created_at);
      return 0;
    });
  };

  const renderedDocs = sortItems((docs || []).filter(d => d.category !== 'media'));
  const renderedMedia = sortItems((docs || []).filter(d => d.category === 'media'));

  const handleDeleteDocument = async (docId) => {
    if (!window.confirm('Are you sure you want to delete this document?')) return;
    try {
      const authToken = localStorage.getItem('token');
      const response = await fetch(`http://localhost:8002/projects/${project.id}/documents/${docId}`, {
        method: 'DELETE',
        headers: {
          ...(authToken ? { 'Authorization': `Bearer ${authToken}` } : {})
        }
      });
      if (response.ok) {
        setDocs(docs.filter(d => d.id !== docId));
      }
    } catch (e) {
      console.error('Delete document failed', e);
    }
  };

  const handleTestConnection = async () => {
    setIsTesting(true);
    setTestResult(null);
    try {
      const authToken = localStorage.getItem('token');
      const response = await fetch(`http://localhost:8002/projects/${project.id}/databases/test`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          ...(authToken ? { 'Authorization': `Bearer ${authToken}` } : {})
        },
        body: JSON.stringify(dbConfig),
      });
      const data = await response.json();
      setTestResult(data);
    } catch (e) {
      setTestResult({ status: 'error', message: 'Failed to reach backend' });
    } finally {
      setIsTesting(false);
    }
  };

  const handleSaveDatabase = async () => {
    setIsLoading(true);
    try {
      const authToken = localStorage.getItem('token');
      const response = await fetch(`http://localhost:8002/projects/${project.id}/databases`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          ...(authToken ? { 'Authorization': `Bearer ${authToken}` } : {})
        },
        body: JSON.stringify(dbConfig),
      });
      if (response.ok) {
        const savedDb = await response.json();
        setDatabases(prev => {
          const idx = prev.findIndex(d => (d.id === savedDb.id && savedDb.id) || d.name === savedDb.name);
          if (idx >= 0) {
            const newDbs = [...prev];
            newDbs[idx] = savedDb;
            return newDbs;
          }
          return [...prev, savedDb];
        });
        setShowDbForm(false);
        setTestResult(null);
        alert('Database configuration saved!');
      }
    } catch (e) {
      console.error('Save database failed', e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteDatabase = async (dbId) => {
    if (!window.confirm('Delete this database configuration?')) return;
    try {
      const authToken = localStorage.getItem('token');
      const response = await fetch(`http://localhost:8002/projects/${project.id}/databases/${dbId}`, {
        method: 'DELETE',
        headers: {
          ...(authToken ? { 'Authorization': `Bearer ${authToken}` } : {})
        }
      });
      if (response.ok) {
        setDatabases(databases.filter(d => d.id !== dbId));
      }
    } catch (e) {
      console.error('Delete database failed', e);
    }
  };

  const sections = [
    { id: 'chat', label: 'Chat', icon: <Sparkles size={18} /> },
    { id: 'docs', label: 'Documents', icon: <FileText size={18} /> },
    { id: 'db', label: 'Databases', icon: <Database size={18} /> },
    { id: 'media', label: 'Media', icon: <ImageIcon size={18} /> },
    { id: 'settings', label: 'Project Settings', icon: <Settings size={18} /> },
    { id: 'access', label: 'Access Control', icon: <ShieldCheck size={18} /> },
  ];

  const handleSaveMarkdown = async (filename, content) => {
    setIsSavingMarkdown(true);
    try {
      const authToken = localStorage.getItem('token');
      const response = await fetch(`http://localhost:8002/projects/${project.id}/markdown/${filename}`, {
        method: 'PUT',
        headers: { 
          'Content-Type': 'application/json',
          ...(authToken ? { 'Authorization': `Bearer ${authToken}` } : {})
        },
        body: JSON.stringify({ content })
      });
      if (response.ok) {
        alert(`${filename} saved successfully!`);
      } else {
        alert(`Failed to save ${filename}`);
      }
    } catch(e) {
      console.error(e);
      alert('Error saving markdown');
    } finally {
      setIsSavingMarkdown(false);
    }
  };



  return (
    <div className="dashboard">
      <button onClick={onBack} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '2rem' }}>
        <ArrowLeft size={18} /> Back to Projects
      </button>

      <div className="dashboard-header">
        <h1 style={{ fontSize: '2.5rem', fontWeight: 800 }}>{project.name}</h1>
        <p style={{ color: 'var(--text-muted)' }}>Project-wise resource management and configuration.</p>
      </div>

      <div style={{ display: 'flex', gap: '2rem', marginBottom: '3rem', borderBottom: '1px solid var(--border-color)' }}>
        {sections.map(s => (
          <button 
            key={s.id}
            onClick={() => setActiveTab(s.id)}
            style={{
              padding: '1rem 0.5rem',
              background: 'transparent',
              border: 'none',
              borderBottom: activeTab === s.id ? '2px solid var(--accent-color)' : 'none',
              color: activeTab === s.id ? 'var(--accent-color)' : 'var(--text-muted)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              fontWeight: 600
            }}
          >
            {s.icon} {s.label}
          </button>
        ))}
      </div>

      <div className="tab-content">
        {activeTab === 'docs' && (
          <div>
            {/* Upload Area at Top */}
            <div style={{ 
              background: 'rgba(255, 255, 255, 0.03)', 
              border: '1px solid var(--border-color)', 
              borderRadius: '16px', 
              padding: '1.2rem', 
              marginBottom: '2rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '1rem'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.8rem' }}>
                  <Plus size={20} color="var(--accent-color)" />
                  <h4 style={{ fontSize: '1rem' }}>Upload New Document</h4>
                </div>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Supported: PDF, DOCX, TXT, Excel</p>
              </div>
              <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                <input 
                  id="file-upload"
                  type="file" 
                  onChange={(e) => setSelectedFile(e.target.files[0])}
                  accept=".pdf,.docx,.doc,.txt,.xls,.xlsx"
                  style={{ 
                    flex: 1,
                    background: 'rgba(0,0,0,0.2)', 
                    border: '1px solid var(--border-color)', 
                    borderRadius: '8px', 
                    padding: '0.5rem',
                    color: 'white',
                    fontSize: '0.9rem'
                  }}
                />
                <button 
                  onClick={handleUploadDocument}
                  disabled={!selectedFile || isLoading}
                  style={{ 
                    background: 'var(--accent-color)', 
                    border: 'none', 
                    color: 'white', 
                    padding: '0.6rem 1.5rem', 
                    borderRadius: '8px', 
                    fontWeight: 600,
                    cursor: (isLoading || !selectedFile) ? 'not-allowed' : 'pointer',
                    opacity: (!selectedFile || isLoading) ? 0.5 : 1,
                    transition: 'all 0.2s',
                    whiteSpace: 'nowrap'
                  }}
                >
                  {isLoading ? 'Uploading...' : 'Upload File'}
                </button>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h3 style={{ fontSize: '1.2rem' }}>Documents ({renderedDocs.length})</h3>
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Sort by:</span>
                <select 
                  value={sortBy} 
                  onChange={(e) => setSortBy(e.target.value)}
                  style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)', color: 'white', padding: '0.4rem 0.8rem', borderRadius: '8px', cursor: 'pointer' }}
                >
                  <option value="date">Date Added</option>
                  <option value="name">Name</option>
                </select>
              </div>
            </div>
            <div className="grid">
              {renderedDocs.slice((docPage - 1) * DOCS_PER_PAGE, docPage * DOCS_PER_PAGE).map(doc => (
                <div key={doc.id} className="project-card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
<FileText size={24} color="var(--accent-color)" />
                    {doc.path && (
                      <button 
                        onClick={() => handleViewFile(doc.id)}
                        style={{ background: 'rgba(255,255,255,0.05)', border: 'none', padding: '0.4rem', borderRadius: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.3rem', color: 'var(--text-muted)', fontSize: '0.8rem' }}
                        title="View Document"
                      >
                        <Eye size={16} /> View
                      </button>
                    )}
                  </div>
                  <h4 style={{ marginTop: '1rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={doc.name}>{doc.name || 'Unnamed Doc'}</h4>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem' }}>
                    <span style={{ 
                      fontSize: '0.7rem', 
                      background: 'rgba(255,255,255,0.1)', 
                      padding: '0.2rem 0.5rem', 
                      borderRadius: '4px', 
                      color: 'var(--accent-color)',
                      fontWeight: 700,
                      textTransform: 'uppercase'
                    }}>
                      {doc.doc_type || (doc.name || '').split('.').pop() || 'TXT'}
                    </span>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {new Date(doc.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end' }}>
                    <button 
                      onClick={() => handleDeleteDocument(doc.id)}
                      style={{ background: 'transparent', border: 'none', color: 'rgba(255,100,100,0.7)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.8rem' }}
                    >
                      <Trash2 size={14} /> Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
            
            <Pagination 
              currentPage={docPage}
              totalPages={Math.ceil(renderedDocs.length / DOCS_PER_PAGE)}
              onPageChange={setDocPage}
            />
          </div>
        )}

        {activeTab === 'chat' && (
          <div style={{ height: '500px', display: 'flex', flexDirection: 'column', background: 'rgba(0,0,0,0.2)', borderRadius: '20px', border: '1px solid var(--border-color)', overflow: 'hidden' }}>
            <Chat 
               selectedProjectId={project.id}
               currentChatId={currentChatId}
               setCurrentChatId={setCurrentChatId}
               chats={Array.isArray(chats) ? chats.filter(c => c.project_id === project.id) : []}
               onChatUpdate={onChatUpdate}
               onDeleteChat={onDeleteChat}
            />
          </div>
        )}

        {activeTab === 'db' && (
          <div style={{ maxWidth: '800px' }}>
            {!showDbForm ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h3 style={{ fontSize: '1.5rem' }}>Database Connections</h3>
                  <button 
                    onClick={() => {
                        setDbConfig({ name: '', host: 'localhost', port: 5432, user: '', password: '', database: '', type: 'postgresql' });
                        setShowDbForm(true);
                    }}
                    style={{ background: 'var(--accent-color)', border: 'none', color: 'white', padding: '0.6rem 1.2rem', borderRadius: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                  >
                    <Plus size={18} /> Add Database
                  </button>
                </div>

                <div className="grid" style={{ gridTemplateColumns: '1fr' }}>
                  {databases.length === 0 ? (
                    <div style={{ padding: '3rem', textAlign: 'center', background: 'rgba(255,255,255,0.02)', borderRadius: '12px', border: '1px dashed var(--border-color)' }}>
                      <Server size={48} color="var(--text-muted)" style={{ margin: '0 auto 1rem', display: 'block' }} />
                      <p style={{ color: 'var(--text-muted)' }}>No databases configured for this project yet.</p>
                    </div>
                  ) : (
                    databases.map(db => (
                      <div key={db.id} className="project-card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                          <Database size={24} color="var(--accent-color)" />
                          <div>
                            <h4 style={{ fontSize: '1.1rem' }}>{db.name || 'Unnamed DB'}</h4>
                            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{db.user}@{db.host}:{db.port}/{db.database}</p>
                          </div>
                        </div>
                        <div style={{ display: 'flex', gap: '1rem' }}>
                          <button 
                            onClick={() => { setDbConfig(db); setShowDbForm(true); }}
                            style={{ background: 'transparent', border: 'none', color: 'var(--accent-color)', cursor: 'pointer', fontSize: '0.85rem' }}
                          >
                            Edit
                          </button>
                          <button 
                            onClick={() => handleDeleteDatabase(db.id)}
                            style={{ background: 'transparent', border: 'none', color: '#ef4444', cursor: 'pointer', fontSize: '0.85rem' }}
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            ) : (
              <div className="project-card">
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '2rem' }}>
                  <Server size={32} color="var(--accent-color)" />
                  <div>
                    <h3 style={{ fontSize: '1.5rem' }}>{dbConfig.id ? 'Edit' : 'Add'} Database</h3>
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>Enter the connection details for this database.</p>
                  </div>
                </div>
                
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
                  <div className="form-group" style={{ gridColumn: 'span 2' }}>
                    <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-muted)' }}>Connection Name (e.g., Staging ERP)</label>
                    <input 
                      type="text" 
                      value={dbConfig.name}
                      onChange={(e) => { setDbConfig({...dbConfig, name: e.target.value}); setTestResult(null); }}
                      placeholder="e.g. Production PostgreSQL"
                      style={{ width: '100%', padding: '0.8rem', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)', color: 'white' }}
                    />
                  </div>
                  <div className="form-group" style={{ gridColumn: 'span 2' }}>
                    <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-muted)' }}>Database Type</label>
                    <select 
                      value={dbConfig.type || 'postgresql'}
                      onChange={(e) => { setDbConfig({...dbConfig, type: e.target.value, port: e.target.value === 'mysql' ? 3306 : 5432}); setTestResult(null); }}
                      style={{ width: '100%', padding: '0.8rem', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)', color: 'white', marginBottom: '1rem' }}
                    >
                      <option value="postgresql">PostgreSQL</option>
                      <option value="mysql">MySQL</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-muted)' }}>Host</label>
                    <input 
                      type="text" 
                      value={dbConfig.host}
                      onChange={(e) => { setDbConfig({...dbConfig, host: e.target.value}); setTestResult(null); }}
                      style={{ width: '100%', padding: '0.8rem', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)', color: 'white' }}
                    />
                  </div>
                  <div className="form-group">
                    <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-muted)' }}>Port</label>
                    <input 
                      type="number" 
                      value={dbConfig.port}
                      onChange={(e) => { setDbConfig({...dbConfig, port: e.target.value}); setTestResult(null); }}
                      style={{ width: '100%', padding: '0.8rem', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)', color: 'white' }}
                    />
                  </div>
                  <div className="form-group">
                    <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-muted)' }}>Username</label>
                    <input 
                      type="text" 
                      value={dbConfig.user}
                      onChange={(e) => { setDbConfig({...dbConfig, user: e.target.value}); setTestResult(null); }}
                      style={{ width: '100%', padding: '0.8rem', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)', color: 'white' }}
                    />
                  </div>
                  <div className="form-group">
                    <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-muted)' }}>Password</label>
                    <input 
                      type="password" 
                      value={dbConfig.password}
                      onChange={(e) => { setDbConfig({...dbConfig, password: e.target.value}); setTestResult(null); }}
                      style={{ width: '100%', padding: '0.8rem', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)', color: 'white' }}
                    />
                  </div>
                  <div className="form-group" style={{ gridColumn: 'span 2' }}>
                    <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-muted)' }}>Database Name</label>
                    <input 
                      type="text" 
                      value={dbConfig.database}
                      onChange={(e) => { setDbConfig({...dbConfig, database: e.target.value}); setTestResult(null); }}
                      style={{ width: '100%', padding: '0.8rem', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)', color: 'white' }}
                    />
                  </div>
                </div>

                {testResult && (
                  <div style={{ 
                    marginTop: '1.5rem', 
                    padding: '1rem', 
                    borderRadius: '8px', 
                    background: testResult.status === 'success' ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                    border: `1px solid ${testResult.status === 'success' ? '#22c55e' : '#ef4444'}`,
                    color: testResult.status === 'success' ? '#22c55e' : '#ef4444',
                    fontSize: '0.9rem'
                  }}>
                    {testResult.message}
                  </div>
                )}

                <div style={{ marginTop: '2.5rem', display: 'flex', gap: '1rem' }}>
                  <button 
                    onClick={handleSaveDatabase}
                     disabled={isLoading || testResult?.status !== 'success'}
                    title={testResult?.status !== 'success' ? "Please test connection successfully before saving" : ""}
                    style={{ 
                      flex: 1, 
                      display: 'flex', 
                      alignItems: 'center', 
                      justifyContent: 'center', 
                      gap: '0.5rem',
                      background: 'var(--accent-color)', 
                      border: 'none', 
                      color: 'white', 
                      padding: '1rem', 
                      borderRadius: '12px', 
                      fontWeight: 600,
                      cursor: (isLoading || testResult?.status !== 'success') ? 'not-allowed' : 'pointer',
                      opacity: (isLoading || testResult?.status !== 'success') ? 0.5 : 1
                    }}
                  >
                    <Save size={20} />
                    {isLoading ? 'Saving...' : 'Save Database'}
                  </button>
                  <button 
                    onClick={handleTestConnection}
                    disabled={isTesting}
                    style={{ 
                      flex: 1, 
                      background: 'rgba(255,255,255,0.05)', 
                      border: '1px solid var(--border-color)', 
                      color: 'white', 
                      padding: '1rem', 
                      borderRadius: '12px', 
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '0.5rem'
                    }}
                  >
                    {isTesting ? 'Testing...' : 'Test Connection'}
                  </button>
                  <button 
                    onClick={() => { setShowDbForm(false); setTestResult(null); }}
                    style={{ background: 'transparent', border: '1px solid #ef4444', color: '#ef4444', padding: '1rem', borderRadius: '12px', cursor: 'pointer' }}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'media' && (
          <div>
            {/* Upload Area at Top */}
            <div style={{ 
              background: 'rgba(255, 255, 255, 0.03)', 
              border: '1px solid var(--border-color)', 
              borderRadius: '16px', 
              padding: '1.2rem', 
              marginBottom: '2rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '1rem'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.8rem' }}>
                  <ImageIcon size={20} color="var(--accent-color)" />
                  <h4 style={{ fontSize: '1rem' }}>Upload New Media</h4>
                </div>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Supported: Images, Video, Audio</p>
              </div>
              <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                <input 
                  id="media-upload"
                  type="file" 
                  onChange={(e) => setSelectedFile(e.target.files[0])}
                  accept="image/*,video/*,audio/*"
                  style={{ 
                    flex: 1,
                    background: 'rgba(0,0,0,0.2)', 
                    border: '1px solid var(--border-color)', 
                    borderRadius: '8px', 
                    padding: '0.5rem',
                    color: 'white',
                    fontSize: '0.9rem'
                  }}
                />
                <button 
                  onClick={handleUploadMedia}
                  disabled={!selectedFile || isLoading}
                  style={{ 
                    background: 'var(--accent-color)', 
                    border: 'none', 
                    color: 'white', 
                    padding: '0.6rem 1.5rem', 
                    borderRadius: '8px', 
                    fontWeight: 600,
                    cursor: (isLoading || !selectedFile) ? 'not-allowed' : 'pointer',
                    opacity: (!selectedFile || isLoading) ? 0.5 : 1,
                    transition: 'all 0.2s',
                    whiteSpace: 'nowrap'
                  }}
                >
                  {isLoading ? 'Uploading...' : 'Upload Asset'}
                </button>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h3 style={{ fontSize: '1.2rem' }}>Media Assets ({renderedMedia.length})</h3>
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Sort by:</span>
                <select 
                  value={sortBy} 
                  onChange={(e) => setSortBy(e.target.value)}
                  style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)', color: 'white', padding: '0.4rem 0.8rem', borderRadius: '8px', cursor: 'pointer' }}
                >
                  <option value="date">Date Added</option>
                  <option value="name">Name</option>
                </select>
              </div>
            </div>
            <div className="grid">
              {renderedMedia.slice((mediaPage - 1) * MEDIA_PER_PAGE, mediaPage * MEDIA_PER_PAGE).map(item => (
                <div key={item.id} className="project-card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <ImageIcon size={24} color="var(--accent-color)" />
                    {item.path && (
                      <button 
                        onClick={() => handleViewFile(item.id)}
                        style={{ background: 'rgba(255,255,255,0.05)', border: 'none', padding: '0.4rem', borderRadius: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.3rem', color: 'var(--text-muted)', fontSize: '0.8rem' }}
                        title="View Asset"
                      >
                        <Eye size={16} /> Preview
                      </button>
                    )}
                  </div>
                  <h4 style={{ marginTop: '1rem' }}>{item.name}</h4>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
                    Added {new Date(item.created_at).toLocaleDateString()}
                  </p>
                  <div style={{ marginTop: '1rem', display: 'flex', justifyContent: 'flex-end' }}>
                    <button 
                      onClick={() => handleDeleteDocument(item.id)}
                      style={{ background: 'transparent', border: 'none', color: '#ef4444', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.85rem' }}
                    >
                      <Trash2 size={16} /> Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
            
            <Pagination 
              currentPage={mediaPage}
              totalPages={Math.ceil(renderedMedia.length / MEDIA_PER_PAGE)}
              onPageChange={setMediaPage}
            />
          </div>
        )}

        {activeTab === 'settings' && (
          <div style={{ maxWidth: '800px', display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            <div className="project-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                <div>
                  <h3 style={{ fontSize: '1.2rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Settings size={20} color="var(--accent-color)" /> Project Guidelines
                  </h3>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
                    Define the rules, context, and core concepts of this project. The AI uses this to strictly route global questions and guardrail the conversation. Format in Markdown.
                  </p>
                </div>
                <button 
                  onClick={() => handleSaveMarkdown('project_guidelines.md', projectGuidelines)}
                  disabled={isSavingMarkdown}
                  style={{ background: 'var(--accent-color)', border: 'none', color: 'white', padding: '0.6rem 1rem', borderRadius: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                >
                  <Save size={16} /> Save
                </button>
              </div>
              <textarea 
                value={projectGuidelines}
                onChange={(e) => setProjectGuidelines(e.target.value)}
                placeholder="# Project Overview\n\nThis project tracks our AI adoption metrics..."
                style={{ width: '100%', height: '200px', padding: '1rem', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)', color: 'white', fontFamily: 'monospace', resize: 'vertical' }}
              />
            </div>

            <div className="project-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                <div>
                  <h3 style={{ fontSize: '1.2rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Database size={20} color="var(--accent-color)" /> Database Schema Context
                  </h3>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
                    Provide a human-readable skeleton of your database tables to help the AI write accurate, specific SQL queries seamlessly. Format in Markdown.
                  </p>
                </div>
                <button 
                  onClick={() => handleSaveMarkdown('db_schema.md', dbSchema)}
                  disabled={isSavingMarkdown}
                  style={{ background: 'var(--accent-color)', border: 'none', color: 'white', padding: '0.6rem 1rem', borderRadius: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                >
                  <Save size={16} /> Save
                </button>
              </div>
              <textarea 
                value={dbSchema}
                onChange={(e) => setDbSchema(e.target.value)}
                placeholder="# Database: staging_db\n\n## Table: users\n- id (int)\n- email (varchar)\n\n## Table: orders\n- id (int)\n- user_id (fk)"
                style={{ width: '100%', height: '300px', padding: '1rem', borderRadius: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)', color: 'white', fontFamily: 'monospace', resize: 'vertical' }}
              />
            </div>
          </div>
        )}

        {activeTab === 'access' && (
          <div className="project-card" style={{ maxWidth: '800px' }}>
            <h3>Collaborators</h3>
            <div style={{ marginTop: '2rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1rem', background: 'rgba(0,0,0,0.2)', borderRadius: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                  <div style={{ width: '40px', height: '40px', borderRadius: '50%', background: 'linear-gradient(45deg, #6366f1, #c084fc)' }}></div>
                  <div>
                    <p>John Doe (Admin)</p>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>john@example.com</p>
                  </div>
                </div>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Full Access</span>
              </div>
            </div>
            <button style={{ marginTop: '2rem', background: 'transparent', border: '1px solid var(--accent-color)', color: 'var(--accent-color)', padding: '0.8rem 1.5rem', borderRadius: '8px', cursor: 'pointer' }}>+ Invite Contributor</button>
          </div>
        )}
      </div>
    </div>
  );
};

export default ProjectDetails;
