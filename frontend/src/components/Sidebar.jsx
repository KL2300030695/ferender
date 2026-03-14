import React from 'react';
import {
  Brain,
  History,
  Settings,
  User,
  Sparkles,
  Heart,
  Activity,
} from 'lucide-react';

const Sidebar = ({ currentSessionActive, historyCount, resilienceScore, empathyLevel, user, logout }) => {
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <Brain size={28} className="pulse" />
        <span>Wellness AI</span>
      </div>

      <nav className="sidebar-section">
        <span className="sidebar-label">Navigation</span>
        <div className="stats-card" style={currentSessionActive ? { background: 'rgba(139, 92, 246, 0.1)', cursor: 'pointer' } : { cursor: 'pointer' }}>
          <div className="emotion-label" style={currentSessionActive ? { color: '#a78bfa' } : {}}>
            <Sparkles size={18} /> Current Session
          </div>
        </div>
        <div className="stats-card" style={{ opacity: historyCount > 0 ? 1 : 0.5, cursor: 'pointer' }}>
          <div className="emotion-label">
            <History size={18} /> History ({historyCount})
          </div>
        </div>
      </nav>

      <div className="sidebar-section">
        <span className="sidebar-label">Emotional Insights</span>
        <div className="stats-card">
          <div className="emotion-label">
            <Activity size={18} /> Resilience Score
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{resilienceScore}%</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {resilienceScore >= 80 ? 'Steady mental clarity' : resilienceScore >= 50 ? 'Finding balance' : 'Needs reflection'}
          </div>
        </div>
        <div className="stats-card">
          <div className="emotion-label">
            <Heart size={18} color="#ef4444" /> Empathy Level
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{empathyLevel}</div>
        </div>
      </div>

      <div style={{ marginTop: 'auto' }} className="sidebar-section">
        <div className="stats-card" style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div className="avatar user"><User size={20} /></div>
            <span style={{ fontWeight: 500, fontSize: '0.95rem' }}>{user ? user.first_name : 'Guest User'}</span>
          </div>
          {user ? (
            <button 
              onClick={logout} 
              style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
              title="Logout"
            >
                <Settings size={20} color="var(--accent-secondary)" style={{ flexShrink: 0 }} />
            </button>
          ) : (
            <Settings size={20} color="var(--text-muted)" style={{ cursor: 'pointer', flexShrink: 0 }} />
          )}
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
