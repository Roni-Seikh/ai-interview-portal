// src/pages/HistoryPage.js
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import Navbar from '../components/common/Navbar';
import api from '../services/api';
import { FiArrowRight, FiClipboard, FiPlay, FiTrendingUp, FiTrendingDown, FiMinus } from 'react-icons/fi';

function GradeBadge({ score }) {
  const grade = score >= 90 ? 'A+' : score >= 80 ? 'A' : score >= 70 ? 'B+' : score >= 60 ? 'B' : score >= 50 ? 'C' : score >= 40 ? 'D' : 'F';
  const cls = score >= 70 ? 'bg-emerald-500/15 text-emerald-300 border-emerald-600/30'
    : score >= 50 ? 'bg-yellow-500/15 text-yellow-300 border-yellow-600/30'
    : 'bg-red-500/15 text-red-300 border-red-600/30';
  return <span className={`text-xs font-bold px-2.5 py-0.5 rounded-full border ${cls}`}>{grade}</span>;
}

function StatusBadge({ status }) {
  const map = {
    completed: 'bg-emerald-500/15 text-emerald-300',
    abandoned: 'bg-slate-500/15 text-slate-400',
    technical_round: 'bg-blue-500/15 text-blue-300',
    hr_round: 'bg-purple-500/15 text-purple-300',
    setup: 'bg-slate-500/15 text-slate-400',
  };
  return <span className={`text-xs px-2 py-0.5 rounded-full ${map[status] || map.setup}`}>{status.replace('_', ' ')}</span>;
}

export default function HistoryPage() {
  const [interviews, setInterviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    api.get('/interview/history')
      .then(res => setInterviews(res.data.interviews))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = interviews.filter(i => filter === 'all' || i.status === filter);

  const getDelta = (idx) => {
    const completed = interviews.filter(i => i.status === 'completed');
    const pos = completed.findIndex(i => i.id === filtered[idx]?.id);
    if (pos <= 0 || filtered[idx]?.status !== 'completed') return null;
    const prev = completed[pos + 1];
    if (!prev) return null;
    return (filtered[idx].overall_score - prev.overall_score).toFixed(1);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <Navbar />
      <div className="max-w-5xl mx-auto px-4 sm:px-6 pt-24 pb-16">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <h1 className="text-3xl font-display font-bold text-white">Interview History</h1>
          <p className="text-slate-400 mt-1">Track your progress and revisit past interviews.</p>
        </motion.div>

        {/* Filters */}
        <div className="flex gap-2 mb-6 flex-wrap">
          {['all', 'completed', 'technical_round', 'hr_round', 'abandoned'].map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${filter === f ? 'bg-primary-600 text-white' : 'bg-slate-800 text-slate-400 hover:text-white'}`}>
              {f === 'all' ? 'All' : f.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-48">
            <div className="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-20 text-slate-400">
            <FiClipboard size={44} className="mx-auto mb-4 opacity-25" />
            <p className="text-lg">No interviews found.</p>
            <Link to="/interview/start" className="mt-4 inline-flex items-center gap-2 bg-primary-600 text-white px-5 py-2.5 rounded-xl hover:bg-primary-500 transition-colors text-sm">
              <FiPlay /> Start one now
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {filtered.map((interview, idx) => {
              const delta = getDelta(idx);
              return (
                <motion.div key={interview.id}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.04 }}
                  className="bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-xl p-5 flex items-center gap-4 transition-colors"
                >
                  {/* Score ring */}
                  <div className="flex-shrink-0">
                    <div className="relative w-14 h-14">
                      <svg viewBox="0 0 36 36" className="w-14 h-14 -rotate-90">
                        <circle cx="18" cy="18" r="14" fill="none" stroke="#1e293b" strokeWidth="3.5" />
                        <circle cx="18" cy="18" r="14" fill="none" stroke="#6366f1" strokeWidth="3.5"
                          strokeDasharray={`${interview.overall_score} 100`} strokeLinecap="round" />
                      </svg>
                      <span className="absolute inset-0 flex items-center justify-center text-xs font-bold text-white">{Math.round(interview.overall_score)}%</span>
                    </div>
                  </div>

                  {/* Details */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="font-semibold text-white truncate">{interview.job_role}</p>
                      <StatusBadge status={interview.status} />
                      {interview.status === 'completed' && <GradeBadge score={interview.overall_score} />}
                    </div>
                    <div className="flex items-center gap-4 mt-1">
                      <span className="text-xs text-slate-500">{new Date(interview.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}</span>
                      {interview.status === 'completed' && (
                        <>
                          <span className="text-xs text-slate-500">Tech: <span className="text-slate-300">{interview.technical_score}%</span></span>
                          <span className="text-xs text-slate-500">HR: <span className="text-slate-300">{interview.hr_score}%</span></span>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Delta indicator */}
                  {delta !== null && (
                    <div className={`flex items-center gap-1 text-xs font-medium ${Number(delta) > 0 ? 'text-emerald-400' : Number(delta) < 0 ? 'text-red-400' : 'text-slate-400'}`}>
                      {Number(delta) > 0 ? <FiTrendingUp size={14} /> : Number(delta) < 0 ? <FiTrendingDown size={14} /> : <FiMinus size={14} />}
                      {delta > 0 ? '+' : ''}{delta}%
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {interview.status === 'completed' && (
                      <Link to={`/results/${interview.id}`}
                        className="flex items-center gap-1.5 text-xs bg-primary-600/15 hover:bg-primary-600/25 text-primary-300 px-3 py-1.5 rounded-lg transition-colors border border-primary-600/20">
                        Results <FiArrowRight size={11} />
                      </Link>
                    )}
                    {['setup', 'technical_round', 'hr_round'].includes(interview.status) && (
                      <Link to={`/interview/${interview.id}`}
                        className="flex items-center gap-1.5 text-xs bg-emerald-600/15 hover:bg-emerald-600/25 text-emerald-300 px-3 py-1.5 rounded-lg transition-colors border border-emerald-600/20">
                        Resume <FiPlay size={11} />
                      </Link>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
