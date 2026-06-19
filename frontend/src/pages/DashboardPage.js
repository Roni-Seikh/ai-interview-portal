// src/pages/DashboardPage.js
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, RadialBarChart, RadialBar } from 'recharts';
import Navbar from '../components/common/Navbar';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';
import {
  FiPlay, FiAward, FiTrendingUp, FiClipboard,
  FiArrowRight, FiAlertCircle
} from 'react-icons/fi';

const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.08 } }
};
const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 }
};

function StatCard({ icon, label, value, color, suffix = '' }) {
  return (
    <motion.div variants={itemVariants} className="bg-slate-900 border border-slate-800 rounded-2xl p-6 flex items-center gap-4">
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${color}`}>
        {icon}
      </div>
      <div>
        <p className="text-sm text-slate-400">{label}</p>
        <p className="text-2xl font-bold text-white">{value}{suffix}</p>
      </div>
    </motion.div>
  );
}

function GradeChip({ score }) {
  const grade = score >= 90 ? 'A+' : score >= 80 ? 'A' : score >= 70 ? 'B+' : score >= 60 ? 'B' : score >= 50 ? 'C' : 'D';
  const color = score >= 70 ? 'text-emerald-400 bg-emerald-400/10' : score >= 50 ? 'text-yellow-400 bg-yellow-400/10' : 'text-red-400 bg-red-400/10';
  return <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${color}`}>{grade}</span>;
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/dashboard/stats')
      .then(res => setStats(res.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <Navbar />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-16">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -16 }} animate={{ opacity: 1, y: 0 }} className="mb-10">
          <p className="text-slate-400 text-sm">{greeting},</p>
          <h1 className="text-3xl font-display font-bold text-white mt-1">
            {user?.full_name?.split(' ')[0]} 👋
          </h1>
          <p className="text-slate-400 mt-1">Track your progress and prepare for your dream job.</p>
        </motion.div>

        {/* Start Interview CTA */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-gradient-to-r from-primary-600 to-primary-800 rounded-2xl p-6 mb-8 flex items-center justify-between"
        >
          <div>
            <h2 className="text-xl font-bold text-white">Ready to practice?</h2>
            <p className="text-primary-200 text-sm mt-1">Start a new AI-powered mock interview tailored to your resume.</p>
          </div>
          <Link
            to="/interview/start"
            className="flex items-center gap-2 bg-white text-primary-700 font-semibold px-5 py-3 rounded-xl hover:bg-primary-50 transition-colors text-sm whitespace-nowrap"
          >
            <FiPlay /> Start Interview
          </Link>
        </motion.div>

        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : stats ? (
          <>
            {/* Stat Cards */}
            <motion.div
              variants={containerVariants}
              initial="hidden"
              animate="show"
              className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8"
            >
              <StatCard
                icon={<FiClipboard className="text-primary-400 text-xl" />}
                label="Total Interviews"
                value={stats.total_interviews}
                color="bg-primary-500/10"
              />
              <StatCard
                icon={<FiAward className="text-emerald-400 text-xl" />}
                label="Avg Score"
                value={stats.avg_score}
                suffix="%"
                color="bg-emerald-500/10"
              />
              <StatCard
                icon={<FiTrendingUp className="text-yellow-400 text-xl" />}
                label="Technical Avg"
                value={stats.avg_technical}
                suffix="%"
                color="bg-yellow-500/10"
              />
              <StatCard
                icon={<FiAlertCircle className="text-blue-400 text-xl" />}
                label="HR Avg"
                value={stats.avg_hr}
                suffix="%"
                color="bg-blue-500/10"
              />
            </motion.div>

            <div className="grid lg:grid-cols-2 gap-6 mb-8">
              {/* Score Trend */}
              {stats.score_trend?.length > 0 && (
                <motion.div variants={itemVariants} initial="hidden" animate="show" className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
                  <h3 className="font-semibold text-white mb-4">Score Trend</h3>
                  <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={stats.score_trend}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 11 }} />
                      <YAxis domain={[0, 100]} tick={{ fill: '#64748b', fontSize: 11 }} />
                      <Tooltip
                        contentStyle={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', color: '#f8fafc' }}
                        formatter={(v) => [`${v}%`, 'Score']}
                      />
                      <Line type="monotone" dataKey="score" stroke="#6366f1" strokeWidth={2} dot={{ fill: '#6366f1', r: 4 }} />
                    </LineChart>
                  </ResponsiveContainer>
                </motion.div>
              )}

              {/* Performance Donut */}
              <motion.div variants={itemVariants} initial="hidden" animate="show" className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
                <h3 className="font-semibold text-white mb-4">Performance Split</h3>
                <div className="flex items-center justify-center gap-8">
                  <div className="text-center">
                    <div className="relative w-24 h-24">
                      <svg viewBox="0 0 36 36" className="w-24 h-24 -rotate-90">
                        <circle cx="18" cy="18" r="15.9" fill="none" stroke="#1e293b" strokeWidth="3.8" />
                        <circle cx="18" cy="18" r="15.9" fill="none" stroke="#6366f1" strokeWidth="3.8"
                          strokeDasharray={`${stats.avg_technical} 100`} strokeLinecap="round" />
                      </svg>
                      <span className="absolute inset-0 flex items-center justify-center text-lg font-bold text-white">{stats.avg_technical}%</span>
                    </div>
                    <p className="text-xs text-slate-400 mt-2">Technical</p>
                  </div>
                  <div className="text-center">
                    <div className="relative w-24 h-24">
                      <svg viewBox="0 0 36 36" className="w-24 h-24 -rotate-90">
                        <circle cx="18" cy="18" r="15.9" fill="none" stroke="#1e293b" strokeWidth="3.8" />
                        <circle cx="18" cy="18" r="15.9" fill="none" stroke="#10b981" strokeWidth="3.8"
                          strokeDasharray={`${stats.avg_hr} 100`} strokeLinecap="round" />
                      </svg>
                      <span className="absolute inset-0 flex items-center justify-center text-lg font-bold text-white">{stats.avg_hr}%</span>
                    </div>
                    <p className="text-xs text-slate-400 mt-2">HR</p>
                  </div>
                </div>
              </motion.div>
            </div>

            {/* Recent Interviews */}
            {stats.recent_interviews?.length > 0 && (
              <motion.div variants={itemVariants} initial="hidden" animate="show" className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold text-white">Recent Interviews</h3>
                  <Link to="/history" className="text-sm text-primary-400 hover:text-primary-300 flex items-center gap-1">
                    View all <FiArrowRight size={14} />
                  </Link>
                </div>
                <div className="space-y-3">
                  {stats.recent_interviews.map(interview => (
                    <div key={interview.id} className="flex items-center justify-between py-3 border-b border-slate-800 last:border-0">
                      <div>
                        <p className="font-medium text-white text-sm">{interview.job_role}</p>
                        <p className="text-xs text-slate-400">{new Date(interview.created_at).toLocaleDateString()}</p>
                      </div>
                      <div className="flex items-center gap-3">
                        <GradeChip score={interview.overall_score} />
                        <span className="text-sm font-semibold text-white">{interview.overall_score}%</span>
                        <Link
                          to={`/results/${interview.id}`}
                          className="text-primary-400 hover:text-primary-300 text-xs flex items-center gap-1"
                        >
                          View <FiArrowRight size={12} />
                        </Link>
                      </div>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </>
        ) : (
          <div className="text-center py-16 text-slate-400">
            <FiClipboard size={40} className="mx-auto mb-4 opacity-30" />
            <p className="text-lg">No interviews yet.</p>
            <Link to="/interview/start" className="mt-4 inline-flex items-center gap-2 bg-primary-600 text-white px-5 py-2.5 rounded-xl hover:bg-primary-500 transition-colors text-sm">
              <FiPlay /> Start your first interview
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
