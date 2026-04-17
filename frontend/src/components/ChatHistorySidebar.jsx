import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Plus, MessageSquare, Trash2, Search } from 'lucide-react';

const ChatHistorySidebar = ({ onSelectChat, activeChatId, onNewChat, chats = [], onDeleteChat, isCollapsed }) => {
  const [searchTerm, setSearchTerm] = useState('');
  
  const [width, setWidth] = useState(280);
  const isResizing = useRef(false);
  const sidebarRef = useRef(null);

  const startResizing = useCallback((e) => {
    isResizing.current = true;
    document.body.style.cursor = 'col-resize';
  }, []);

  const stopResizing = useCallback(() => {
    isResizing.current = false;
    document.body.style.cursor = 'default';
  }, []);

  const resize = useCallback((e) => {
    if (isResizing.current && sidebarRef.current) {
      const rect = sidebarRef.current.getBoundingClientRect();
      const newWidth = e.clientX - rect.left;
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

  const filteredChats = chats.filter(c => 
    (c.title || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleDelete = (e, id) => {
    e.stopPropagation();
    onDeleteChat(id);
  };

  return (
    <div 
      ref={sidebarRef} 
      className={`chat-sidebar ${isCollapsed ? 'collapsed' : ''}`} 
      style={{ width: isCollapsed ? 0 : width, minWidth: isCollapsed ? 0 : width, position: 'relative' }}
    >
      <div className="resize-handle" onMouseDown={startResizing} />
      <div className="sidebar-header">
        <button className="new-chat-btn" onClick={onNewChat}>
          <Plus size={18} />
          <span>New Chat</span>
        </button>
      </div>

      <div className="sidebar-search">
        <Search size={16} className="search-icon" />
        <input 
          type="text" 
          placeholder="Search chats..." 
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
      </div>

      <div className="sidebar-content">
        {filteredChats.length === 0 ? (
          <div className="sidebar-empty">No chats found</div>
        ) : (
          filteredChats.map(chat => (
            <div 
              key={chat.id} 
              className={`sidebar-item ${activeChatId === chat.id ? 'active' : ''}`}
              onClick={() => onSelectChat(chat.id)}
            >
              <MessageSquare size={16} className="item-icon" />
              <div className="item-info">
                <span className="item-title">{chat.title || 'Untitled Chat'}</span>
                <span className="item-date">
                  {new Date(chat.last_message_at).toLocaleDateString()}
                </span>
              </div>
              <button 
                className="delete-btn" 
                onClick={(e) => handleDelete(e, chat.id)}
                title="Delete chat"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))
        )}
      </div>


    </div>
  );
};

export default ChatHistorySidebar;
