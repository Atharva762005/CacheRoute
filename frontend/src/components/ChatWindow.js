// PropIQ ChatWindow Component
import React, { useState, useRef, useEffect } from 'react';
import { parsePropertyInput, generateBotResponse } from '../utils/chatParser';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';



export default function ChatWindow({ form, onFormUpdate, onAssess, onPDF, loading, result }) {
  const [messages, setMessages] = useState([
    {
      id: 1, role: 'bot',
      text: "Hi! I'm **PropIQ** 👋\n\nTell me about a property to assess, or ask me anything about collateral underwriting.\n\nOnce you run an assessment, I can answer specific questions about the valuation, risk flags, LTV, and more.",
    },
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const bottomRef = useRef(null);
  // Keep history for Groq context (role: 'user'|'assistant')
  const historyRef = useRef([]);
  const pendingAutoAssessRef = useRef(false);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // ── Agentic auto-assess: trigger assessment after form auto-fill ──────
  useEffect(() => {
    if (pendingAutoAssessRef.current && form.locality && form.prop_type &&
        form.size_sqft && form.age_years !== '') {
      pendingAutoAssessRef.current = false;
      const tid = setTimeout(() => onAssess({ keepDrawer: true }), 500);
      return () => clearTimeout(tid);
    }
  }, [form, onAssess]);

  const addMessage = (role, text, extra = {}) => {
    setMessages(prev => [...prev, { id: Date.now(), role, text, ...extra }]);
  };

  const handleSend = async (text) => {
    const msg = text || input.trim();
    if (!msg) return;
    setInput('');
    addMessage('user', msg);

    // ── 1. Parse property fields from natural language (local, instant) ──
    const { extracted, missing } = parsePropertyInput(msg);
    const updatedForm = { ...form, ...extracted };
    if (Object.keys(extracted).length > 0) onFormUpdate(updatedForm);

    // ── 2. Check if this looks like a full property description ─────────────
    const lowerMsg = msg.toLowerCase();
    const hasEnoughForAutoAssess = extracted.locality && extracted.prop_type &&
      (extracted.size_sqft || extracted.age_years !== undefined);

    // ── 3. Simple command triggers (skip when full description → let backend LLM handle) ──
    if (!hasEnoughForAutoAssess) {
      const isAssessAction = lowerMsg.includes('assess') || lowerMsg.includes('value') ||
        lowerMsg.includes('valuat') || lowerMsg.includes('how much') ||
        lowerMsg.includes('worth') || lowerMsg.includes('price');
      const isPdfAction = lowerMsg.includes('pdf') || lowerMsg.includes('report') || lowerMsg.includes('download');

      if (isAssessAction) {
        addMessage('bot', 'Running the assessment now...');
        setTimeout(() => onAssess({ keepDrawer: true }), 300);
        historyRef.current.push({ role: 'user', content: msg },
          { role: 'assistant', content: 'Running the assessment now...' });
        return;
      }
      if (isPdfAction) {
        addMessage('bot', 'Generating your RBI-ready PDF report...');
        setTimeout(() => onPDF(), 300);
        historyRef.current.push({ role: 'user', content: msg },
          { role: 'assistant', content: 'Generating your RBI-ready PDF report...' });
        return;
      }
    }

    // ── 3. Call Groq via backend /api/v1/chat ─────────────────────────────
    setIsTyping(true);
    historyRef.current.push({ role: 'user', content: msg });

    try {
      const res = await fetch(`${API_BASE}/api/v1/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: historyRef.current,
          form_context: updatedForm,
          assessment_result: result || null,
        }),
      });
      const data = await res.json();
      const reply = data.reply || "I didn't understand that. Could you rephrase?";
      setIsTyping(false);

      // ── Handle agentic auto-assess ───────────────────────────────────
      if (data.action === 'auto_assess' && data.extracted_fields) {
        const fields = data.extracted_fields;
        const autoForm = {
          locality: fields.locality,
          prop_type: fields.prop_type,
          size_sqft: fields.size_sqft,
          age_years: fields.age_years,
          floor_num: fields.floor_num ?? 3,
          is_freehold: fields.is_freehold ?? 1,
          is_rera_registered: fields.is_rera_registered ?? 1,
          occupancy: fields.occupancy || 'self_occupied',
          rental_yield_pct: fields.rental_yield_pct || 0,
        };
        onFormUpdate(autoForm);
        addMessage('bot', reply);
        historyRef.current.push({ role: 'assistant', content: reply });
        pendingAutoAssessRef.current = true;
        return;
      }

      // ── Normal reply ────────────────────────────────────────────────
      addMessage('bot', reply);
      historyRef.current.push({ role: 'assistant', content: reply });
    } catch (err) {
      console.error('Chat API error:', err);
      setIsTyping(false);
      // Graceful fallback to local rule-based response
      const { text: botText } = generateBotResponse(msg, updatedForm, missing);
      addMessage('bot', botText);
      historyRef.current.push({ role: 'assistant', content: botText });
    }
  };

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  // Render markdown-lite (bold + italic + newlines)
  const renderText = (text) => {
    const parts = text.split(/(\*\*.*?\*\*|\*.*?\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**'))
        return <strong key={i}>{part.slice(2, -2)}</strong>;
      if (part.startsWith('*') && part.endsWith('*'))
        return <em key={i}>{part.slice(1, -1)}</em>;
      return part.split('\n').map((line, j) =>
        j === 0 ? line : [<br key={j} />, line]
      );
    });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 16px 8px', display: 'flex',
                    flexDirection: 'column', gap: 12 }}>
        {messages.map(msg => (
          <div key={msg.id} style={{
            display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
            alignItems: 'flex-end', gap: 8,
          }}>
            {msg.role === 'bot' && (
              <div style={{ width: 28, height: 28, borderRadius: '50%',
                background: 'linear-gradient(135deg, #534AB7, #1D9E75)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 13, flexShrink: 0, color: '#fff', fontWeight: 700 }}>P</div>
            )}
            <div style={{
              maxWidth: '78%', padding: '10px 14px',
              background: msg.role === 'user' ? '#534AB7' : '#fff',
              color: msg.role === 'user' ? '#fff' : '#2C2C2A',
              borderRadius: msg.role === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
              fontSize: 13, lineHeight: 1.6,
              boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
              border: msg.role === 'bot' ? '1px solid rgba(44,44,42,0.08)' : 'none',
            }}>
              {renderText(msg.text)}
            </div>
          </div>
        ))}

        {(loading || isTyping) && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 28, height: 28, borderRadius: '50%',
              background: 'linear-gradient(135deg, #534AB7, #1D9E75)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 13, color: '#fff', fontWeight: 700 }}>P</div>
            <div style={{ background: '#fff', border: '1px solid rgba(44,44,42,0.08)',
              borderRadius: '16px 16px 16px 4px', padding: '12px 16px',
              display: 'flex', gap: 4, alignItems: 'center' }}>
              {[0,1,2].map(i => (
                <div key={i} style={{
                  width: 7, height: 7, borderRadius: '50%', background: '#534AB7',
                  animation: `bounce 1.2s ease-in-out ${i * 0.2}s infinite`,
                }} />
              ))}
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Assessment grounded indicator */}
      {result && (
        <div style={{
          margin: '0 16px 6px',
          padding: '6px 12px',
          background: 'linear-gradient(135deg, #E1F5EE, #EEEDFE)',
          borderRadius: 8,
          fontSize: 11,
          color: '#0F6E56',
          fontWeight: 600,
          display: 'flex',
          alignItems: 'center',
          gap: 6,
        }}>
          <span>✅</span>
          <span>Assessment loaded · Ask me anything about {result.locality || 'this property'}</span>
        </div>
      )}



      {/* Input */}
      <div style={{ padding: '8px 16px 16px', display: 'flex', gap: 8 }}>
        <input value={input} onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey} placeholder="Describe the property..."
          style={{
            flex: 1, padding: '10px 14px', border: '1.5px solid rgba(44,44,42,0.15)',
            borderRadius: 24, fontSize: 13, outline: 'none', fontFamily: 'Inter, sans-serif',
            background: '#fff',
          }} />
        <button onClick={() => handleSend()} disabled={!input.trim() || loading}
          style={{
            width: 40, height: 40, borderRadius: '50%',
            background: input.trim() ? '#534AB7' : '#D3D1C7',
            border: 'none', cursor: input.trim() ? 'pointer' : 'default',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#fff', fontSize: 16, transition: 'background 0.2s',
            flexShrink: 0,
          }}>→</button>
      </div>

      <style>{`
        @keyframes bounce {
          0%, 60%, 100% { transform: translateY(0); }
          30% { transform: translateY(-6px); }
        }
      `}</style>
    </div>
  );
}