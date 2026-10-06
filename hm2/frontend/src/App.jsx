import { useState, useEffect, useRef } from 'react'
import './index.css'

function generateId() {
  return Math.random().toString(36).substr(2, 9)
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

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
        <h2>Operation History</h2>
        <div className="history-list">
          {history.length === 0 ? (
            <p style={{color: 'var(--text-tertiary)', fontSize: '0.85rem'}}>No recent operations.</p>
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
          <h2>Database Agent</h2>
        </div>
        
        <div className="messages-container">
          <div className="messages">
            {messages.length === 0 && (
              <div style={{color: 'var(--text-secondary)', textAlign: 'center', margin: '60px auto', maxWidth: '400px'}}>
                <h3 style={{color: 'var(--text-primary)', marginBottom: '12px'}}>How can I help you today?</h3>
                <p style={{fontSize: '0.95rem', lineHeight: '1.5'}}>I am connected to the Supabase database. You can ask me to list, create, update, or safely delete employee records.</p>
              </div>
            )}
            
            {messages.map((msg, i) => (
              <div key={i} className={`message-wrapper ${msg.role}`}>
                <div className={`message ${msg.role} ${msg.isError ? 'error' : ''}`}>
                  {msg.role === 'user' ? (
                    <div>{msg.content}</div>
                  ) : (
                    <>
                      <div style={{whiteSpace: 'pre-wrap'}}>{msg.content}</div>
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
