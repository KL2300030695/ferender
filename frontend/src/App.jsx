import React, { useState, useEffect, useRef, useCallback } from 'react';
import Webcam from 'react-webcam';
import axios from 'axios';
import {
  Send,
  Mic,
  Smile,
  Brain,
  History,
  Settings,
  User,
  Sparkles,
  Heart,
  Activity,
  ChevronRight
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';

const API_BASE_URL = 'http://localhost:8000';

const App = () => {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: "Hello! I'm your AI Wellness Companion. I can see how you're feeling through your camera and I'm here to listen. How are you today?" }
  ]);
  const [inputText, setInputText] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentEmotion, setCurrentEmotion] = useState('neutral');
  const [confidence, setConfidence] = useState(0);

  const webcamRef = useRef(null);
  const messagesEndRef = useRef(null);
  const chatContainerRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);

  // Real-time Emotion Detection
  const captureAndDetect = useCallback(async () => {
    if (webcamRef.current) {
      const imageSrc = webcamRef.current.getScreenshot();
      if (imageSrc) {
        try {
          const response = await axios.post(`${API_BASE_URL}/detect-emotion`, { image: imageSrc });
          setCurrentEmotion(response.data.emotion);
          setConfidence(response.data.confidence);
        } catch (error) {
          console.error("Emotion detection error:", error);
        }
      }
    }
  }, []);

  useEffect(() => {
    const interval = setInterval(captureAndDetect, 3000);
    return () => clearInterval(interval);
  }, [captureAndDetect]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!inputText.trim() || isStreaming) return;

    const userMessage = { role: 'user', content: inputText };
    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setIsStreaming(true);

    // Placeholder for AI streaming message
    const aiMessageIndex = messages.length + 1;
    setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [...messages, userMessage],
          current_emotion: currentEmotion
        })
      });

      if (!response.ok) throw new Error("Failed to connect to backend");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let accumulatedText = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        accumulatedText += chunk;

        setMessages(prev => {
          const newMessages = [...prev];
          newMessages[newMessages.length - 1].content = accumulatedText;
          return newMessages;
        });
      }
    } catch (error) {
      console.error("Chat error:", error);
      setMessages(prev => {
        const newMessages = [...prev];
        newMessages[newMessages.length - 1].content = "Sorry, I encountered an error connecting to my wisdom cluster. Please make sure Ollama is running.";
        return newMessages;
      });
    } finally {
      setIsStreaming(false);
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <Brain size={28} className="pulse" />
          <span>Wellness AI</span>
        </div>

        <nav className="sidebar-section">
          <span className="sidebar-label">Navigation</span>
          <div className="stats-card" style={{ background: 'rgba(139, 92, 246, 0.1)', cursor: 'pointer' }}>
            <div className="emotion-label" style={{ color: '#a78bfa' }}>
              <Sparkles size={18} /> Current Session
            </div>
          </div>
          <div className="stats-card" style={{ opacity: 0.5 }}>
            <div className="emotion-label">
              <History size={18} /> History
            </div>
          </div>
        </nav>

        <div className="sidebar-section">
          <span className="sidebar-label">Emotional Insights</span>
          <div className="stats-card">
            <div className="emotion-label">
              <Activity size={18} /> Resilience Score
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>84%</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Steady mental clarity</div>
          </div>
          <div className="stats-card">
            <div className="emotion-label">
              <Heart size={18} color="#ef4444" /> Empathy Level
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>Elite</div>
          </div>
        </div>

        <div style={{ marginTop: 'auto' }} className="sidebar-section">
          <div className="stats-card" style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div className="avatar user"><User size={20} /></div>
              <span>Guest User</span>
            </div>
            <Settings size={20} color="var(--text-muted)" />
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        <header className="chat-header">
          <h2 className="font-display">Mindful Conversation</h2>
          <div style={{ display: 'flex', gap: 12 }}>
            <div className="emotion-badge" style={{ marginTop: 0 }}>
              <span className="emotion-label">
                <Smile size={18} /> {currentEmotion}
              </span>
            </div>
          </div>
        </header>

        <div className="messages-container" ref={chatContainerRef}>
          <AnimatePresence>
            {messages.map((msg, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, ease: "easeOut" }}
                className="message-wrapper"
              >
                <div className={`avatar ${msg.role === 'assistant' ? 'ai' : 'user'}`}>
                  {msg.role === 'assistant' ? <Sparkles size={20} color="white" /> : <User size={20} color="white" />}
                </div>
                <div className="message-content">
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                  {i === messages.length - 1 && isStreaming && (
                    <span className="pulse" style={{ display: 'inline-block', width: 8, height: 16, background: 'var(--accent-primary)', marginLeft: 4, borderRadius: 2 }} />
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
          <div ref={messagesEndRef} />
        </div>

        <div className="input-container">
          <form onSubmit={handleSend} className="input-wrapper">
            <input
              type="text"
              className="chat-input"
              placeholder="Tell me how you're feeling..."
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              disabled={isStreaming}
            />
            <button type="submit" className="send-button" disabled={!inputText.trim() || isStreaming}>
              <Send size={20} />
            </button>
          </form>
          <p style={{ textAlign: 'center', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 12 }}>
            Wellness AI can make mistakes. Consider checking important information.
          </p>
        </div>
      </main>

      {/* Video Overlay */}
      <div className="video-overlay">
        <div className="webcam-preview">
          <Webcam
            audio={false}
            ref={webcamRef}
            screenshotFormat="image/jpeg"
            videoConstraints={{ width: 400, height: 300, facingMode: "user" }}
          />
        </div>
        <div className="emotion-badge">
          <span className="emotion-label">
            <Activity size={16} /> {currentEmotion}
          </span>
          <div className="confidence-ring" style={{ borderColor: `hsla(${confidence * 120}, 70%, 50%, 0.5)` }}>
            {Math.round(confidence * 100)}%
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;
