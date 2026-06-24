import React, { useState, useEffect, useRef, useCallback } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation, useNavigate } from 'react-router-dom';
import { MessageSquare, LayoutGrid, Settings, User, Box, Plus, Trash2 } from 'lucide-react';
import Chat from './components/Chat';
import Projects from './components/Projects';
import SettingsPage from './components/Settings';
import './App.css';

const Sidebar = ({ projects, selectedProjectId, setSelectedProjectId, chats, currentChatId, setCurrentChatId, onNewChat, onDeleteChat }) => {
  const location = useLocation();
  const navigate = useNavigate();
  
  const [width, setWidth] = useState(260);
  const isResizing = useRef(false);

  const startResizing = useCallback((e) => {
    isResizing.current = true;
    document.body.style.cursor = 'col-resize';
  }, []);

  const stopResizing = useCallback(() => {
    isResizing.current = false;
    document.body.style.cursor = 'default';
  }, []);

  const resize = useCallback((e) => {
    if (isResizing.current) {
      const newWidth = e.clientX;
      if (newWidth > 200 && newWidth < 500) {
        setWidth(newWidth);
      }
    }
  }, []);

  useEffect(() => {
    window.addEventListener('mousemove', resize);
    window.addEventListener('mouseup', stopResizing);
    return () => {
      window.removeEventListener('mousemove', resize);
      window.removeEventListener('mouseup', stopResizing);
    };
  }, [resize, stopResizing]);

  const navItems = [
    { path: '/', icon: <MessageSquare size={20} />, label: 'Chat' },
    { path: '/projects', icon: <LayoutGrid size={20} />, label: 'Projects' },
    { path: '/settings', icon: <Settings size={20} />, label: 'Settings' },
  ];

  return (
    <div className="sidebar" style={{ width, minWidth: width, position: 'relative' }}>
      <div className="resize-handle" onMouseDown={startResizing} />
      <div className="nav-logo">Enterprise RAG</div>
      
      {/* Chat History Section moved to Chat.jsx */}


      <div className="sidebar-section">
        <div className="sidebar-label">ACTIVE PROJECT</div>
        <div className="project-selector-wrapper">
          <Box size={16} className="selector-icon" />
          <select 
            value={selectedProjectId}
            onChange={(e) => {
              setSelectedProjectId(e.target.value);
              setCurrentChatId(null);
              navigate('/');
            }}
            className="sidebar-project-select"
          >
            <option value="">General Chat</option>
            {projects.map(p => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="nav-menu">
        <div className="sidebar-label">NAVIGATION</div>
        {navItems.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            className={`nav-item ${location.pathname === item.path ? 'active' : ''}`}
          >
            {item.icon}
            <span>{item.label}</span>
          </Link>
        ))}
      </div>

      <div style={{ marginTop: 'auto' }}>
        <div className="nav-item">
          <User size={20} />
          <span>Admin User</span>
        </div>
      </div>
    </div>
  );
};

function App() {
  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [chats, setChats] = useState([]);
  const [currentChatId, setCurrentChatId] = useState(null);

  useEffect(() => {
    fetchProjects();
    fetchChats();
  }, []);

  const fetchProjects = async () => {
    try {
      const res = await fetch('http://localhost:8002/projects');
      const data = await res.json();
      setProjects(data);
    } catch (err) {
      console.error("Failed to fetch projects", err);
    }
  };

  const fetchChats = async () => {
    try {
      const res = await fetch('http://localhost:8002/chats');
      const data = await res.json();
      setChats(data);
      if (data.length > 0 && !currentChatId) {
        // Don't auto-select to avoid overwhelming, but maybe we should for ChatGPT feel.
        // Let's not auto-select for now to preserve the "General Chat" clean start if needed.
      }
    } catch (err) {
      console.error("Failed to fetch chats", err);
    }
  };

  const handleNewChat = async () => {
    try {
      const response = await fetch('http://localhost:8002/chats', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: selectedProjectId ? parseInt(selectedProjectId) : null })
      });
      const newChat = await response.json();
      setChats([newChat, ...chats]);
      setCurrentChatId(newChat.id);
    } catch (err) {
      console.error("Failed to create new chat", err);
    }
  };

  const handleDeleteChat = async (id) => {
    if (!window.confirm('Delete this chat history?')) return;
    try {
      await fetch(`http://localhost:8002/chats/${id}`, { method: 'DELETE' });
      setChats(chats.filter(c => c.id !== id));
      if (currentChatId === id) setCurrentChatId(null);
    } catch (err) {
      console.error("Failed to delete chat", err);
    }
  };

  return (
    <Router>
      <div className="app-container">
        <Sidebar 
          projects={projects} 
          selectedProjectId={selectedProjectId} 
          setSelectedProjectId={setSelectedProjectId} 
          chats={chats}
          currentChatId={currentChatId}
          setCurrentChatId={setCurrentChatId}
          onNewChat={handleNewChat}
          onDeleteChat={handleDeleteChat}
        />
        <main className="main-content">
          <Routes>
            <Route path="/" element={
              <Chat 
                selectedProjectId={selectedProjectId} 
                currentChatId={currentChatId} 
                setCurrentChatId={setCurrentChatId}
                chats={chats}
                onChatUpdate={fetchChats}
                onDeleteChat={handleDeleteChat}
              />
            } />
            <Route path="/projects" element={<Projects 
              projects={projects} 
              setProjects={setProjects} 
              setSelectedProjectId={setSelectedProjectId} 
              chats={chats}
              currentChatId={currentChatId}
              setCurrentChatId={setCurrentChatId}
              onChatUpdate={fetchChats}
              onDeleteChat={handleDeleteChat}
            />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
