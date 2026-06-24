import React, { useState, useEffect } from 'react';
import { Database, FileText, Share2, Info, Plus, X, Trash2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import ProjectDetails from './ProjectDetails';
import Pagination from './Pagination';

const Modal = ({ isOpen, onClose, children, title }) => {
  if (!isOpen) return null;
  return (
    <div style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', background: 'rgba(0,0,0,0.8)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, backdropFilter: 'blur(5px)' }}>
      <div style={{ background: '#111', border: '1px solid var(--border-color)', borderRadius: '20px', width: '90%', maxWidth: '500px', padding: '2rem', position: 'relative' }}>
        <button onClick={onClose} style={{ position: 'absolute', top: '1rem', right: '1rem', background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}><X size={24} /></button>
        <h2 style={{ marginBottom: '1.5rem' }}>{title}</h2>
        {children}
      </div>
    </div>
  );
};

const Projects = ({ projects, setProjects, setSelectedProjectId, chats, currentChatId, setCurrentChatId, onChatUpdate, onDeleteChat }) => {
  const [selectedProject, setSelectedProject] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newProject, setNewProject] = useState({ name: '', status: 'Active', docs: 0, db: 'Default' });
  const [currentPage, setCurrentPage] = useState(1);
  const PROJECTS_PER_PAGE = 6;
  const navigate = useNavigate();
  
  const fetchProjects = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:8002/projects', {
        headers: {
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        }
      });
      const data = await response.json();
      setProjects(data);
    } catch (e) {
      console.error('Failed to fetch projects', e);
    }
  };

  const handleSetActive = (e, projectId) => {
    e.stopPropagation();
    setSelectedProjectId(projectId.toString());
    navigate('/');
  };

  const handleCreateProject = async () => {
    if (!newProject.name) return;
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:8002/projects', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify(newProject),
      });
      if (response.ok) {
        setIsModalOpen(false);
        setNewProject({ name: '', status: 'Active', docs: 0, db: 'Default' });
        fetchProjects();
      }
    } catch (e) {
      console.error('Failed to create project', e);
    }
  };
  const handleDeleteProject = async (e, projectId) => {
    e.stopPropagation(); // Don't trigger the card click
    if (!window.confirm('Are you sure you want to delete this entire project and all its documents? This action cannot be undone.')) return;
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`http://localhost:8002/projects/${projectId}`, {
        method: 'DELETE',
        headers: {
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        }
      });
      if (response.ok) {
        fetchProjects();
      }
    } catch (e) {
      console.error('Failed to delete project', e);
    }
  };

  if (selectedProject) {
    return <ProjectDetails 
      project={selectedProject} 
      onBack={() => setSelectedProject(null)} 
      chats={chats}
      currentChatId={currentChatId}
      setCurrentChatId={setCurrentChatId}
      onChatUpdate={onChatUpdate}
      onDeleteChat={onDeleteChat}
    />;
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: '2.5rem', fontWeight: 800 }}>Projects</h1>
          <p style={{ color: 'var(--text-muted)', marginTop: '0.5rem' }}>Manage your data sources and knowledge bases project-wise.</p>
        </div>
        <button 
          onClick={() => setIsModalOpen(true)}
          style={{ 
            background: 'var(--accent-color)', 
            border: 'none', 
            color: 'white', 
            padding: '0.8rem 1.5rem', 
            borderRadius: '12px',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            fontWeight: 600,
            cursor: 'pointer'
          }}
        >
          <Plus size={20} />
          New Project
        </button>
      </div>

      <div className="grid">
        {projects.slice((currentPage - 1) * PROJECTS_PER_PAGE, currentPage * PROJECTS_PER_PAGE).map(project => (
          <div key={project.id} className="project-card" onClick={() => setSelectedProject(project)}>
            <div className={`badge ${project.status === 'Active' ? 'badge-blue' : 'badge-green'}`}>
              {project.status}
            </div>
            <h3 style={{ fontSize: '1.4rem', marginBottom: '1rem' }}>{project.name}</h3>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <FileText size={16} />
                <span>{project.docs || 0} Documents (PDF, DOCX)</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Database size={16} />
                <span>Database: {project.db || 'None'}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Share2 size={16} />
                <span>Access: 1 User (Private)</span>
              </div>
            </div>

            <div style={{ marginTop: '2rem', paddingTop: '1.5rem', borderTop: '1px solid var(--border-color)', display: 'flex', gap: '1rem', alignItems: 'center' }}>
              <button 
                onClick={(e) => { e.stopPropagation(); setSelectedProject(project); }}
                className="nav-item" style={{ flex: 1, justifyContent: 'center' }}
              >
                Manage Resources
              </button>
              <button 
                onClick={(e) => handleSetActive(e, project.id)}
                style={{ 
                  background: 'rgba(99, 102, 241, 0.1)', 
                  border: '1px solid rgba(99, 102, 241, 0.3)', 
                  color: 'var(--accent-color)', 
                  padding: '0.4rem 0.8rem', 
                  borderRadius: '8px',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                Activate for Chat
              </button>
              <button 
                onClick={(e) => handleDeleteProject(e, project.id)}
                style={{ background: 'transparent', border: 'none', color: '#ef4444', cursor: 'pointer', padding: '0.4rem', borderRadius: '8px' }}
                title="Delete Project"
              >
                <Trash2 size={18} />
              </button>
            </div>
          </div>
        ))}
      </div>

      <Pagination 
        currentPage={currentPage}
        totalPages={Math.ceil(projects.length / PROJECTS_PER_PAGE)}
        onPageChange={setCurrentPage}
      />

      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title="Create New Project">
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-muted)' }}>Project Name</label>
            <input 
              type="text" 
              value={newProject.name}
              onChange={(e) => setNewProject({...newProject, name: e.target.value})}
              style={{ width: '100%', padding: '0.8rem', borderRadius: '8px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-color)', color: 'white' }}
              placeholder="e.g. Sales Analysis 2024"
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-muted)' }}>Initial Status</label>
            <select 
              value={newProject.status}
              onChange={(e) => setNewProject({...newProject, status: e.target.value})}
              style={{ width: '100%', padding: '0.8rem', borderRadius: '8px', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-color)', color: 'white' }}
            >
              <option value="Active">Active</option>
              <option value="Indexing">Indexing</option>
              <option value="On Hold">On Hold</option>
            </select>
          </div>
          <button 
            onClick={handleCreateProject}
            style={{ marginTop: '1rem', background: 'var(--accent-color)', border: 'none', color: 'white', padding: '1rem', borderRadius: '12px', fontWeight: 600, cursor: 'pointer' }}
          >
            Create Project
          </button>
        </div>
      </Modal>
    </div>
  );
};

export default Projects;
