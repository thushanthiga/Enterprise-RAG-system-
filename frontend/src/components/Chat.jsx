import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Send, Sparkles, Sidebar as SidebarIcon } from 'lucide-react';
import ChatHistorySidebar from './ChatHistorySidebar';

const Chat = ({ selectedProjectId, currentChatId, setCurrentChatId, chats, onChatUpdate, onDeleteChat }) => {
  const [messages, setMessages] = useState([
    { role: 'ai', content: 'Hello! I am your Enterprise RAG assistant. Select a project from the sidebar to begin chatting.' }
  ]);
  const [input, setInput] = useState('');
  const [searchMode, setSearchMode] = useState('auto');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(scrollToBottom, [messages]);

  useEffect(() => {
    if (currentChatId) {
      loadChatHistory(currentChatId);
    } else {
      setMessages([
        { role: 'ai', content: 'Hello! I am your Enterprise RAG assistant. Select a project or start a new chat to begin.' }
      ]);
    }
  }, [currentChatId]);

  const loadChatHistory = async (id) => {
    try {
      const response = await fetch(`http://localhost:8002/chats/${id}`);
      if (response.ok) {
        const data = await response.json();
        setMessages((data && Array.isArray(data.messages)) ? data.messages : [
          { role: 'ai', content: `Continuing chat: ${data?.title || 'Untitled'}` }
        ]);
      }
    } catch (e) {
      console.error("Failed to load chat history", e);
    }
  };

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMsg = { role: 'user', content: input };
    const currentInput = input;
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsTyping(true);

    try {
      // If no currentChatId, create one first
      let activeChatId = currentChatId;
      if (!activeChatId) {
        const createRes = await fetch('http://localhost:8002/chats', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ project_id: selectedProjectId ? parseInt(selectedProjectId) : null })
        });
        const newChat = await createRes.json();
        activeChatId = newChat.id;
        setCurrentChatId(activeChatId);
        onChatUpdate(); // Refresh sidebar
      }

      // Use the actual streaming endpoint
      const response = await fetch('http://localhost:8002/ask/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          question: currentInput, 
          user_id: 'dev',
          project_id: selectedProjectId ? parseInt(selectedProjectId) : null,
          chat_id: activeChatId,
          search_mode: searchMode
        }),
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let aiResponse = '';
      
      setMessages(prev => [...prev, { role: 'ai', content: '' }]);
      setIsTyping(false); // Stop "Thinking..." once stream starts

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') break;
            
            try {
              const parsed = JSON.parse(data);
              if (parsed.token) {
                aiResponse += parsed.token;
                setMessages(prev => {
                  const newMsgs = [...prev];
                  if (newMsgs.length === 0) {
                    newMsgs.push({ role: 'user', content: currentInput });
                    newMsgs.push({ role: 'ai', content: aiResponse });
                  } else {
                    newMsgs[newMsgs.length - 1] = { ...newMsgs[newMsgs.length - 1], content: aiResponse };
                  }
                  return newMsgs;
                });
              } else if (parsed.metadata) {
                // --- Structured Console Trace ---
                console.groupCollapsed(`%c🔍 RAG Pipeline Trace: "${currentInput.substring(0, 30)}..."`, "color: #4CAF50; font-weight: bold; font-size: 1.1em;");
                console.log(`%c📝 Input Data`, "color: #2196F3; font-weight: bold;", {
                  Query: currentInput,
                  ChatID: activeChatId,
                  ProjectID: selectedProjectId || "None",
                  Mode: searchMode
                });
                console.log(`%c🧭 Router Agent`, "color: #FF9800; font-weight: bold;", {
                  Intent: parsed.metadata.intent || "Unknown",
                  Reasoning: parsed.metadata.router_debug || "Static/Fallback",
                });
                console.log(`%c⚙️ Orchestrator Agent`, "color: #9C27B0; font-weight: bold;", {
                  SQL_Executed: parsed.metadata.sql || "None",
                  Documents_Retrieved: parsed.metadata.docs?.length ? parsed.metadata.docs.map(d => d.name || d.source || "Unknown DOC") : "None",
                  Context_Injected: parsed.metadata.injected_files?.length ? parsed.metadata.injected_files : "None",
                  Rows_Returned: parsed.metadata.total_rows ?? "N/A"
                });
                console.log(`%c✨ Final State`, "color: #E91E63; font-weight: bold;", "Response fully synthesized.");
                console.groupEnd();
                
                setMessages(prev => {
                  const newMsgs = [...prev];
                  if (newMsgs.length > 0) {
                    newMsgs[newMsgs.length - 1] = { ...newMsgs[newMsgs.length - 1], metadata: parsed.metadata };
                  }
                  return newMsgs;
                });
              }
            } catch (e) {
              console.error('Error parsing stream chunk', e);
            }
          }
        }
      }
      onChatUpdate(); // Refresh sidebar for potential title change
    } catch (error) {
      setMessages(prev => [...prev, { role: 'ai', content: 'Sorry, I encountered an error connecting to the backend.' }]);
    } finally {
      setIsTyping(false);
    }
  };

  const [isSidebarVisible, setIsSidebarVisible] = useState(true);

  return (
    <div className={`chat-container ${!isSidebarVisible ? 'sidebar-collapsed' : ''}`}>
      <ChatHistorySidebar 
        onSelectChat={setCurrentChatId}
        activeChatId={currentChatId}
        chats={chats}
        onDeleteChat={onDeleteChat}
        isCollapsed={!isSidebarVisible}
        onNewChat={() => {
          const handleInternalNewChat = async () => {
            const response = await fetch('http://localhost:8002/chats', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ project_id: selectedProjectId ? parseInt(selectedProjectId) : null })
            });
            const newChat = await response.json();
            setCurrentChatId(newChat.id);
            onChatUpdate(); 
          };
          handleInternalNewChat();
        }}
      />
      
      <div className="chat-window">
        <div className="chat-header">
          <button 
            className="sidebar-toggle-btn" 
            onClick={() => setIsSidebarVisible(!isSidebarVisible)}
            title={isSidebarVisible ? "Hide Sidebar" : "Show Sidebar"}
          >
            <SidebarIcon size={20} />
          </button>
        </div>
        <div className="messages-container">
          {messages.map((msg, idx) => (
            <div key={idx} className={`message ${msg.role}`}>
              <div className="markdown-body">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {msg.content || ''}
                </ReactMarkdown>
              </div>
            </div>
          ))}
          {isTyping && (
            <div className="message ai" style={{ opacity: 0.6 }}>
              Thinking...
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* ── Sticky footer: mode selector + input ── */}
        <div className="chat-footer">
          <div className="search-mode-selector">
            <button 
              className={`mode-btn ${searchMode === 'auto' ? 'active' : ''}`} 
              onClick={() => setSearchMode('auto')}
            >
              <Sparkles size={14} /> Auto
            </button>
            <button 
              className={`mode-btn ${searchMode === 'db' ? 'active' : ''}`} 
              onClick={() => setSearchMode('db')}
            >
              Database
            </button>
            <button 
              className={`mode-btn ${searchMode === 'doc' ? 'active' : ''}`} 
              onClick={() => setSearchMode('doc')}
            >
              Documents
            </button>
          </div>

          <div className="chat-input-container">
            <Sparkles size={20} color="var(--accent-color)" />
            <input
              type="text"
              className="chat-input"
              placeholder="Ask me anything about your documents or data..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            />
            <button className="send-btn" onClick={handleSend} title="Send Message">
              <Send size={20} />
            </button>
          </div>
        </div>
      </div>


    </div>
  );
};

export default Chat;
