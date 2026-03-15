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
  ChevronRight,
  Volume2,
  VolumeX,
  MicOff
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import { useAuth } from '../context/AuthContext';
import Sidebar from '../components/Sidebar';

const API_BASE_URL = 'http://localhost:8000';

const Dashboard = () => {
  const { user, logout } = useAuth();
  const [messages, setMessages] = useState([
    { role: 'assistant', content: `Hello${user ? ' ' + user.first_name : ''}! I'm your AI Wellness Companion. I can see how you're feeling through your camera and I'm here to listen. How are you today?` }
  ]);
  const [inputText, setInputText] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentEmotion, setCurrentEmotion] = useState('neutral');
  const [confidence, setConfidence] = useState(0);

  // Voice State
  const [isListening, setIsListening] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(true);

  // Dynamic Sidebar State
  const [emotionLog, setEmotionLog] = useState([]);
  const [resilienceScore, setResilienceScore] = useState(100);
  const [empathyLevel, setEmpathyLevel] = useState('Aware');
  const [historyCount, setHistoryCount] = useState(0);

  const webcamRef = useRef(null);
  const messagesEndRef = useRef(null);
  const chatContainerRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);

  // Web Speech API references
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const recognitionRef = useRef(null);

  useEffect(() => {
    if (SpeechRecognition && !recognitionRef.current) {
        recognitionRef.current = new SpeechRecognition();
        recognitionRef.current.continuous = false;
        recognitionRef.current.interimResults = true;
        recognitionRef.current.lang = 'en-US';

        recognitionRef.current.onresult = (event) => {
            const transcript = Array.from(event.results)
                .map(result => result[0])
                .map(result => result.transcript)
                .join('');
            setInputText(transcript);
        };

        recognitionRef.current.onerror = (event) => {
            console.error("Speech recognition error", event.error);
            setIsListening(false);
        };

        recognitionRef.current.onend = () => {
            setIsListening(false);
        };
    }
  }, []);

  const toggleListening = () => {
      if (!recognitionRef.current) {
          alert("Your browser does not support Speech Recognition. Please try Chrome or Safari.");
          return;
      }
      
      if (isListening) {
          recognitionRef.current.stop();
          setIsListening(false);
      } else {
          try {
            recognitionRef.current.start();
            setIsListening(true);
          } catch(e) {
            console.error("Speech API Error:", e);
          }
      }
  };

  const speakText = (text) => {
      if (!voiceEnabled || !window.speechSynthesis) return;
      
      window.speechSynthesis.cancel(); // Stop any ongoing speech
      const plainText = text.replace(/[*_~`#]/g, ''); // Basic markdown stripping
      
      const utterance = new SpeechSynthesisUtterance(plainText);
      const voices = window.speechSynthesis.getVoices();
      const preferredVoice = voices.find(v => v.lang.startsWith('en') && (v.name.includes('Female') || v.name.includes('Google'))) || voices.find(v => v.lang.startsWith('en'));
      if (preferredVoice) utterance.voice = preferredVoice;
      
      window.speechSynthesis.speak(utterance);
  };

  // Real-time Emotion Detection
  const captureAndDetect = useCallback(async () => {
    if (webcamRef.current) {
      const imageSrc = webcamRef.current.getScreenshot();
      if (imageSrc) {
        try {
          const response = await axios.post(`${API_BASE_URL}/detect-emotion`, { image: imageSrc });
          const newEmotion = response.data.emotion;
          setCurrentEmotion(newEmotion);
          setConfidence(response.data.confidence);
          
          // Log emotion for stats
          setEmotionLog(prev => {
            const updatedLog = [...prev, newEmotion];
            // Keep last 100 emotion readings to calculate resilience
            if (updatedLog.length > 100) updatedLog.shift();
            return updatedLog;
          });
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

  // Calculate dynamic stats based on emotion log and messages
  useEffect(() => {
    if (emotionLog.length === 0) return;

    // Resilience Calculation: Positive & Neutral vs Negative (angry, disgust, fear, sad)
    const negativeEmotions = ['angry', 'disgust', 'fear', 'sad'];
    const negativeCount = emotionLog.filter(e => negativeEmotions.includes(e)).length;
    const resilience = Math.max(0, 100 - (negativeCount / emotionLog.length) * 100);
    setResilienceScore(Math.round(resilience));

    // Empathy Level Calculation based on interaction length
    const interactionLength = messages.length;
    if (interactionLength > 15) setEmpathyLevel('Elite');
    else if (interactionLength > 8) setEmpathyLevel('High');
    else if (interactionLength > 3) setEmpathyLevel('Engaged');
    else setEmpathyLevel('Aware');

  }, [emotionLog, messages.length]);

  // Load history count on mount
  useEffect(() => {
    const savedSessions = localStorage.getItem('wellness_sessions');
    if (savedSessions) {
      setHistoryCount(JSON.parse(savedSessions).length);
    }

    const saveSession = () => {
      // Only save if there was actual interaction
      if (messages.length > 1) {
        const history = JSON.parse(localStorage.getItem('wellness_sessions') || '[]');
        history.push({
          date: new Date().toISOString(),
          resilienceScore,
          empathyLevel,
          messagesCount: messages.length,
          primaryEmotion: currentEmotion
        });
        localStorage.setItem('wellness_sessions', JSON.stringify(history));
      }
    };

    window.addEventListener('beforeunload', saveSession);
    return () => {
      window.removeEventListener('beforeunload', saveSession);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages.length, resilienceScore, empathyLevel, currentEmotion]);

  const handleSend = async (e) => {
    if (e) e.preventDefault();
    if (!inputText.trim() || isStreaming) return;
    
    // Stop ongoing speech
    if (window.speechSynthesis) window.speechSynthesis.cancel();

    const userMessage = { role: 'user', content: inputText };
    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setIsStreaming(true);

    // Placeholder for AI streaming message
    const aiMessageIndex = messages.length + 1;
    setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

    const token = localStorage.getItem('wellness_token');

    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'Authorization': token ? `Bearer ${token}` : ''
        },
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
      
      if (voiceEnabled) {
          speakText(accumulatedText);
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
      <Sidebar 
        currentSessionActive={messages.length > 1}
        historyCount={historyCount}
        resilienceScore={resilienceScore}
        empathyLevel={empathyLevel}
        user={user}
        logout={logout}
      />

      {/* Main Content */}
      <main className="main-content">
        <header className="chat-header">
          <h2 className="font-display">Mindful Conversation</h2>
          <div style={{ display: 'flex', gap: 12 }}>
            <button 
                onClick={() => {
                    if (window.speechSynthesis && voiceEnabled) window.speechSynthesis.cancel();
                    setVoiceEnabled(!voiceEnabled);
                }}
                style={{ background: 'none', border: 'none', color: voiceEnabled ? 'var(--accent-primary)' : 'var(--text-muted)', cursor: 'pointer', padding: 4 }}
                title={voiceEnabled ? "Mute AI Voice" : "Enable AI Voice"}
            >
                {voiceEnabled ? <Volume2 size={20} /> : <VolumeX size={20} />}
            </button>
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
          <form onSubmit={handleSend} className="input-wrapper" style={{ display: 'flex', alignItems: 'center' }}>
            <button 
                type="button" 
                onClick={toggleListening}
                style={{ 
                    background: 'none', 
                    border: 'none', 
                    color: isListening ? '#ef4444' : 'var(--text-muted)', 
                    cursor: 'pointer', 
                    padding: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginRight: '8px'
                }}
                title={isListening ? "Stop Listening" : "Start Voice Input"}
                disabled={isStreaming}
            >
                {isListening ? <Mic className="pulse" size={20} /> : <MicOff size={20} />}
            </button>
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

export default Dashboard;
