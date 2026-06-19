// src/pages/AdminPage.js
import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import Navbar from '../components/common/Navbar';
import api from '../services/api';
import toast from 'react-hot-toast';
import { FiUsers, FiClipboard, FiAlertTriangle, FiBarChart2, FiToggleLeft, FiToggleRight } from 'react-icons/fi';

function StatCard({ icon, label, value, color }) {
  return (
    <div className={`bg-slate-900 border border-slate-800 rounded-xl p-5 flex items-center gap-4`}>
      <div className={`w-11 h-11 rounded-xl flex items-center justify-center ${color}`}>{icon}</div>
      <div>
        <p className="text-slate-400 text-sm">{label}</p>
        <p className="text-2xl font-bold text-white">{value}</p>
      </div>
    </div>
  );
}

export default function AdminPage() {
  const [tab, setTab] = useState('overview');
  const [analytics, setAnalytics] = useState(null);
  const [users, setUsers] = useState([]);
  const [interviews, setInterviews] = useState([]);
  const [violations, setViolations] = useState([]);
  const [loading, setLoading] = useState(true);

  const tabClass = (t) => `px-4 py-2 rounded-lg text-sm font-medium transition-all ${tab === t ? 'bg-primary-600 text-white' : 'text-slate-400 hover:text-white'}`;

  useEffect(() => {
    Promise.all([
      api.get('/admin/analytics'),
      api.get('/admin/users'),
      api.get('/admin/interviews'),
      api.get('/admin/violations'),
    ]).then(([a, u, i, v]) => {
      setAnalytics(a.data);
      setUsers(u.data.users);
      setInterviews(i.data.interviews);
      setViolations(v.data.violations);
    }).catch(() => toast.error('Failed to load admin data'))
      .finally(() => setLoading(false));
  }, []);

  const toggleUser = async (userId) => {
    try {
      const res = await api.put(`/admin/users/${userId}/toggle`);
      setUsers(prev => prev.map(u => u.id === userId ? res.data.user : u));
      toast.success(res.data.message);
    } catch {
      toast.error('Failed to toggle user');
    }
  };

  if (loading) return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center">
      <div className="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <Navbar />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 pt-24 pb-16">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <h1 className="text-3xl font-display font-bold text-white">Admin Panel</h1>
          <p className="text-slate-400 mt-1">Manage users, monitor interviews and violations.</p>
        </motion.div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 flex-wrap">
          {['overview', 'users', 'interviews', 'violations'].map(t => (
            <button key={t} onClick={() => setTab(t)} className={tabClass(t)}>
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>

        {/* Overview */}
        {tab === 'overview' && analytics && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              <StatCard icon={<FiUsers className="text-primary-400 text-xl" />} label="Total Students" value={analytics.total_users} color="bg-primary-500/10" />
              <StatCard icon={<FiClipboard className="text-emerald-400 text-xl" />} label="Total Interviews" value={analytics.total_interviews} color="bg-emerald-500/10" />
              <StatCard icon={<FiBarChart2 className="text-yellow-400 text-xl" />} label="Avg Score" value={`${analytics.avg_score}%`} color="bg-yellow-500/10" />
              <StatCard icon={<FiAlertTriangle className="text-red-400 text-xl" />} label="Completion Rate" value={`${analytics.completion_rate}%`} color="bg-red-500/10" />
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
              <h3 className="font-semibold text-white mb-4">Recent Violations</h3>
              {violations.slice(0, 5).length === 0 ? (
                <p className="text-slate-400 text-sm">No violations recorded.</p>
              ) : (
                <div className="space-y-2">
                  {violations.slice(0, 5).map((v, i) => (
                    <div key={i} className="flex items-center justify-between py-2 border-b border-slate-800 last:border-0">
                      <div>
                        <span className="text-sm text-white">{v.type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</span>
                        <span className="text-xs text-slate-400 ml-2">Interview #{v.interview_id}</span>
                      </div>
                      <span className="text-xs text-slate-500">{new Date(v.occurred_at).toLocaleString()}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        )}

        {/* Users */}
        {tab === 'users' && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-800 text-left">
                      <th className="px-4 py-3 text-slate-400 font-medium">Name</th>
                      <th className="px-4 py-3 text-slate-400 font-medium">Email</th>
                      <th className="px-4 py-3 text-slate-400 font-medium">Role</th>
                      <th className="px-4 py-3 text-slate-400 font-medium">Verified</th>
                      <th className="px-4 py-3 text-slate-400 font-medium">Joined</th>
                      <th className="px-4 py-3 text-slate-400 font-medium">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map(u => (
                      <tr key={u.id} className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors">
                        <td className="px-4 py-3 text-white font-medium">{u.full_name}</td>
                        <td className="px-4 py-3 text-slate-300">{u.email}</td>
                        <td className="px-4 py-3">
                          <span className={`text-xs px-2 py-0.5 rounded-full ${u.role === 'admin' ? 'bg-yellow-500/20 text-yellow-300' : 'bg-primary-500/20 text-primary-300'}`}>{u.role}</span>
                        </td>
                        <td className="px-4 py-3">
                          <span className={`text-xs ${u.is_verified ? 'text-emerald-400' : 'text-red-400'}`}>{u.is_verified ? '✓ Yes' : '✗ No'}</span>
                        </td>
                        <td className="px-4 py-3 text-slate-400">{new Date(u.created_at).toLocaleDateString()}</td>
                        <td className="px-4 py-3">
                          <button onClick={() => toggleUser(u.id)}
                            className={`flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-lg transition-colors ${u.is_active ? 'text-red-400 hover:bg-red-900/20' : 'text-emerald-400 hover:bg-emerald-900/20'}`}>
                            {u.is_active ? <><FiToggleLeft />Deactivate</> : <><FiToggleRight />Activate</>}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </motion.div>
        )}

        {/* Interviews */}
        {tab === 'interviews' && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-800 text-left">
                      <th className="px-4 py-3 text-slate-400 font-medium">#</th>
                      <th className="px-4 py-3 text-slate-400 font-medium">Job Role</th>
                      <th className="px-4 py-3 text-slate-400 font-medium">Status</th>
                      <th className="px-4 py-3 text-slate-400 font-medium">Score</th>
                      <th className="px-4 py-3 text-slate-400 font-medium">Violations</th>
                      <th className="px-4 py-3 text-slate-400 font-medium">Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {interviews.map(i => (
                      <tr key={i.id} className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors">
                        <td className="px-4 py-3 text-slate-400">#{i.id}</td>
                        <td className="px-4 py-3 text-white">{i.job_role}</td>
                        <td className="px-4 py-3">
                          <span className={`text-xs px-2 py-0.5 rounded-full ${i.status === 'completed' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-slate-500/20 text-slate-400'}`}>
                            {i.status.replace('_', ' ')}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-white">{i.overall_score ? `${i.overall_score}%` : '—'}</td>
                        <td className="px-4 py-3">
                          <span className={`text-xs ${i.violation_count > 0 ? 'text-red-400' : 'text-slate-400'}`}>{i.violation_count}</span>
                        </td>
                        <td className="px-4 py-3 text-slate-400">{new Date(i.created_at).toLocaleDateString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </motion.div>
        )}

        {/* Violations */}
        {tab === 'violations' && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-800 text-left">
                      <th className="px-4 py-3 text-slate-400 font-medium">Interview</th>
                      <th className="px-4 py-3 text-slate-400 font-medium">Violation Type</th>
                      <th className="px-4 py-3 text-slate-400 font-medium">Description</th>
                      <th className="px-4 py-3 text-slate-400 font-medium">Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {violations.map((v, i) => (
                      <tr key={i} className="border-b border-slate-800/50 hover:bg-red-900/10 transition-colors">
                        <td className="px-4 py-3 text-slate-300">#{v.interview_id}</td>
                        <td className="px-4 py-3">
                          <span className="text-xs bg-red-500/15 text-red-300 px-2 py-0.5 rounded-full border border-red-600/20">
                            {v.type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-slate-400">{v.description || '—'}</td>
                        <td className="px-4 py-3 text-slate-500">{new Date(v.occurred_at).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
