import { useState, useEffect, useRef, useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import mermaid from 'mermaid'
import './index.css'

mermaid.initialize({ startOnLoad: false, theme: 'default' })

function MermaidChart({ chart }) {
  const chartRef = useRef(null)
  
  useEffect(() => {
    if (chartRef.current && chart) {
      mermaid.render(`mermaid-${Math.random().toString(36).substr(2, 9)}`, chart).then((res) => {
        chartRef.current.innerHTML = res.svg
      })
    }
  }, [chart])

  return <div className="mermaid-chart" ref={chartRef} />
}

function generateId() {
  return Math.random().toString(36).substr(2, 9)
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const markdownComponents = {
  code({node, inline, className, children, ...props}) {
    const match = /language-(\w+)/.exec(className || '')
    if (!inline && match && match[1] === 'mermaid') {
      return <MermaidChart chart={String(children).replace(/\n$/, '')} />
    }
    return !inline ? (
      <pre className={className} {...props}>
        <code className={className} {...props}>
          {children}
        </code>
      </pre>
    ) : (
      <code className={className} {...props}>
        {children}
      </code>
    )
  }
}

export default function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [history, setHistory] = useState([])
  const [conversationId] = useState(generateId())
  
  const messagesEndRef = useRef(null)
  const textareaRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  useEffect(() => {
    fetchHistory()
  }, [])

  const handleInput = (e) => {
    setInput(e.target.value)
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  async function fetchHistory() {
    try {
      const res = await fetch(`${API_BASE_URL}/api/history`)
      if (res.ok) {
        const data = await res.json()
        setHistory(data.history || [])
      }
    } catch (e) {
      console.error("Failed to fetch history", e)
    }
  }

  async function handleSend(e) {
    if (e) e.preventDefault()
    if (!input.trim() || loading) return

    const userMsg = input.trim()
    setInput('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
    
    setMessages(prev => [...prev, { role: 'user', content: userMsg }])
    setLoading(true)

    try {
      const res = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg, conversation_id: conversationId })
      })
      
      const data = await res.json()
      
      setMessages(prev => [...prev, {
        role: 'ai',
        content: data.message,
        action: data.action,
        requiresApproval: data.requires_approval
      }])
      
      fetchHistory()
    } catch (error) {
      setMessages(prev => [...prev, { role: 'ai', content: "Failed to connect to the backend server.", isError: true }])
    } finally {
      setLoading(false)
    }
  }

  async function handleApproval(endpoint, details = null) {
    setLoading(true)
    try {
      const body = { conversation_id: conversationId }
      if (details) body.details = details

      const res = await fetch(`${API_BASE_URL}/api/hitl/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      })
      
      if (!res.ok) throw new Error("Approval failed")
        
      const data = await res.json()

      setMessages(prev => {
        const newMsgs = [...prev]
        newMsgs[newMsgs.length - 1] = {
          role: 'ai',
          content: data.message,
          requiresApproval: data.requires_approval || false,
          action: data.action || null
        }
        return newMsgs
      })
      
      fetchHistory()
    } catch (e) {
      setMessages(prev => [...prev, { role: 'ai', content: 'Failed to process the requested action.', isError: true }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app-container">
      <aside className="sidebar">
        <h2>
          <svg className="sidebar-title-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
          </svg>
          Operation History
        </h2>
        <div className="history-list">
          {history.length === 0 ? (
            <p className="history-empty">No operations yet.<br/>Try asking me something.</p>
          ) : (
            history.map(item => (
              <div key={item.id} className={`history-item status-${item.status}`}>
                <div className="op">{item.operation} {item.entity}</div>
                <div className="target">{item.target}</div>
                <div className="status">{item.status}</div>
              </div>
            ))
          )}
        </div>
      </aside>

      <main className="main-chat">
        <div className="chat-header">
          <div className="chat-header-left">
            <div className="agent-badge">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
              </svg>
            </div>
            <div className="chat-header-text">
              <h2>Database Agent</h2>
              <span>Gemini · LangGraph · Supabase</span>
            </div>
          </div>
          <div className="status-dot">Live</div>
        </div>
        
        <div className="messages-container">
          <div className="messages">
            {messages.length === 0 && (
              <div className="empty-state">
                <div className="empty-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <ellipse cx="12" cy="5" rx="9" ry="3"></ellipse>
                    <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path>
                    <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path>
                  </svg>
                </div>
                <h3>How can I help you?</h3>
                <p>I'm connected to your Supabase database. Ask me to list, create, update, or safely delete employee records.</p>
                <div className="suggestion-chips">
                  {['Show all employees', 'Add a new employee', 'Show HR department', 'Delete an employee'].map(s => (
                    <button key={s} className="chip" onClick={() => { setInput(s); textareaRef.current?.focus() }}>{s}</button>
                  ))}
                </div>
              </div>
            )}
            
            {messages.map((msg, i) => (
              <div key={i} className={`message-wrapper ${msg.role}`}>
                <div className={`message ${msg.role} ${msg.isError ? 'error' : ''}`}>
                  {msg.role === 'user' ? (
                    <div>{msg.content}</div>
                  ) : (
                    <>
                      <div className="markdown-content">
                        <ReactMarkdown 
                          remarkPlugins={[remarkGfm]}
                          components={markdownComponents}
                        >
                          {msg.content}
                        </ReactMarkdown>
                      </div>
                      {msg.requiresApproval && (
                        <ApprovalCard 
                          action={msg.action} 
                          onApprove={() => handleApproval('approve')}
                          onDecline={() => handleApproval('decline')}
                          onDetails={(details) => handleApproval('details', details)}
                          loading={loading}
                        />
                      )}
                    </>
                  )}
                </div>
              </div>
            ))}
            
            {loading && (
              <div className="message-wrapper ai">
                <div className="message ai">
                  <div className="dot-loading">
                    <span></span><span></span><span></span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        <div className="input-container">
          <form className="input-area" onSubmit={handleSend}>
            <textarea 
              ref={textareaRef}
              rows="1"
              placeholder="Message Database Agent..." 
              value={input}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              disabled={loading}
              autoFocus
            />
            <button type="submit" className="send-btn" disabled={loading || !input.trim()}>
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
              </svg>
            </button>
          </form>
        </div>
      </main>
    </div>
  )
}

function ApprovalCard({ action, onApprove, onDecline, onDetails, loading }) {
  const [showDetailsInput, setShowDetailsInput] = useState(false)
  const [detailsText, setDetailsText] = useState('')

  return (
    <div className="approval-card">
      <h3>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
        Action requires confirmation
      </h3>
      <div className="approval-details">
        <p><strong>Operation:</strong> {action?.operation?.toUpperCase()}</p>
        <p><strong>Target:</strong> {action?.filters && typeof action.filters === 'object' ? Object.values(action.filters).join(' · ') : (action?.target || 'unknown')}</p>
      </div>
      
      {!showDetailsInput ? (
        <div className="approval-actions">
          <button className="danger" onClick={onApprove} disabled={loading}>Confirm Delete</button>
          <button className="secondary" onClick={onDecline} disabled={loading}>Cancel</button>
          <button className="secondary" onClick={() => setShowDetailsInput(true)} disabled={loading}>Refine Criteria</button>
        </div>
      ) : (
        <div className="details-input">
          <input 
            type="text" 
            placeholder="e.g. 'Delete the one in IT'" 
            value={detailsText}
            onChange={e => setDetailsText(e.target.value)}
            autoFocus
            onKeyDown={(e) => {
              if (e.key === 'Enter') onDetails(detailsText)
            }}
          />
          <div className="approval-actions">
            <button className="primary" onClick={() => onDetails(detailsText)} disabled={loading || !detailsText.trim()}>Submit Refinement</button>
            <button className="secondary" onClick={() => setShowDetailsInput(false)} disabled={loading}>Cancel</button>
          </div>
        </div>
      )}
    </div>
  )
}
