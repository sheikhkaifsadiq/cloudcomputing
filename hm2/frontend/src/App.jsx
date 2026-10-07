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

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  useEffect(() => {
    fetchHistory()
  }, [])

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
      setMessages(prev => [...prev, { role: 'ai', content: "I couldn't connect to the backend. Please try again." }])
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
      setMessages(prev => [...prev, { role: 'ai', content: 'Failed to process action. Please try again.' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app-container">
      <aside className="sidebar">
        <h2>History</h2>
        <div className="history-list">
          {history.length === 0 ? (
            <p style={{color: 'var(--text-light)', fontSize: '0.85rem'}}>No operations yet.</p>
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
          <h2>HM2 Assistant</h2>
        </div>
        
        <div className="messages">
          {messages.length === 0 && (
            <div style={{color: 'var(--text-light)', textAlign: 'center', marginTop: '40px'}}>
              Ask HM2 to manage employee data...
            </div>
          )}
          
          {messages.map((msg, i) => (
            <div key={i} className={`message ${msg.role}`}>
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
          ))}
          {loading && (
            <div className="message ai">
              <div className="dot-loading">
                <span></span><span></span><span></span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <form className="input-area" onSubmit={handleSend}>
          <input 
            type="text" 
            placeholder="Ask HM2 to manage employee data... ➤" 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
          />
          <button type="submit" className="primary send-btn" disabled={loading || !input.trim()}>
            Send
          </button>
        </form>
      </main>
    </div>
  )
}

function ApprovalCard({ action, onApprove, onDecline, onDetails, loading }) {
  const [showDetailsInput, setShowDetailsInput] = useState(false)
  const [detailsText, setDetailsText] = useState('')

  return (
    <div className="approval-card">
      <h3>Action requires approval</h3>
      <div className="approval-details">
        <p><strong>Operation:</strong> {action?.operation?.toUpperCase()}</p>
        <p><strong>Target:</strong> {action?.filters && typeof action.filters === 'object' ? Object.values(action.filters).join(' · ') : (action?.target || 'unknown')}</p>
        <p style={{marginTop: '8px', color: 'var(--text-light)'}}>This action will permanently remove the record.</p>
      </div>
      
      {!showDetailsInput ? (
        <div className="approval-actions">
          <button className="danger" onClick={onApprove} disabled={loading}>Approve</button>
          <button onClick={onDecline} disabled={loading}>Decline</button>
          <button onClick={() => setShowDetailsInput(true)} disabled={loading}>Add Details</button>
        </div>
      ) : (
        <div className="details-input">
          <input 
            type="text" 
            placeholder="Additional details..." 
            value={detailsText}
            onChange={e => setDetailsText(e.target.value)}
            autoFocus
          />
          <div className="approval-actions">
            <button className="primary" onClick={() => onDetails(detailsText)} disabled={loading || !detailsText.trim()}>Submit</button>
            <button onClick={() => setShowDetailsInput(false)} disabled={loading}>Cancel</button>
          </div>
        </div>
      )}
    </div>
  )
}
