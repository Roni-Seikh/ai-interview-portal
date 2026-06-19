// src/pages/ResultsPage.js
import React, { useEffect, useState, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid
} from 'recharts';
import Navbar from '../components/common/Navbar';
import api from '../services/api';
import toast from 'react-hot-toast';
import {
  FiDownload, FiArrowLeft, FiCheckCircle, FiXCircle,
  FiAlertCircle, FiBook, FiStar, FiExternalLink,
  FiTarget, FiVolume2, FiRefreshCw
} from 'react-icons/fi';

/* ── tiny helpers ──────────────────────────────────────────── */
function ScoreRing({ score, label, color }) {
  const r = 54, circ = 2 * Math.PI * r;
  const dash = ((score || 0) / 100) * circ;
  return (
    <div className="flex flex-col items-center">
      <div className="relative w-32 h-32">
        <svg width="128" height="128" viewBox="0 0 128 128">
          <circle cx="64" cy="64" r={r} fill="none" stroke="#1e293b" strokeWidth="10"/>
          <circle cx="64" cy="64" r={r} fill="none" stroke={color} strokeWidth="10"
            strokeDasharray={`${dash} ${circ}`} strokeDashoffset={circ / 4}
            strokeLinecap="round" style={{ transition: 'stroke-dasharray 1s ease' }}/>
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-2xl font-bold text-white">{(score || 0).toFixed(0)}%</span>
        </div>
      </div>
      <p className="text-sm text-slate-400 mt-2">{label}</p>
    </div>
  );
}

function Card({ title, children, className = '' }) {
  return (
    <div className={`bg-slate-900 border border-slate-800 rounded-xl p-5 ${className}`}>
      {title && <h3 className="font-semibold text-white mb-4 text-sm">{title}</h3>}
      {children}
    </div>
  );
}

/* ── main component ────────────────────────────────────────── */
export default function ResultsPage() {
  const { id } = useParams();
  const [data, setData]           = useState(null);
  const [loading, setLoading]     = useState(true);
  const [tab, setTab]             = useState('overview');
  const [generating, setGenerating] = useState(false);
  const [regen, setRegen]         = useState(false);
  const [speaking, setSpeaking]   = useState(false);

  const fetchData = useCallback(() => {
    setLoading(true);
    api.get(`/results/${id}`)
      .then(res => setData(res.data))
      .catch(() => toast.error('Failed to load results'))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    fetchData();
    return () => window.speechSynthesis?.cancel();
  }, [fetchData]);

  /* ── voice ── */
  const speakSummary = () => {
    if (!window.speechSynthesis) return toast.error('Browser does not support TTS');
    if (speaking) { window.speechSynthesis.cancel(); setSpeaking(false); return; }
    const { result, feedback, interview } = data || {};
    const text = [
      `Results for ${interview?.job_role}.`,
      `Overall: ${(result?.overall_percentage || 0).toFixed(0)}%, Grade ${result?.grade}.`,
      `Technical: ${(result?.technical_percentage || 0).toFixed(0)}%. HR: ${(result?.hr_percentage || 0).toFixed(0)}%.`,
      feedback?.overall_summary || '',
      feedback?.strengths?.length ? `Strengths: ${feedback.strengths.join('. ')}.` : '',
      feedback?.technical_gaps?.length ? `Study: ${feedback.technical_gaps.join(', ')}.` : '',
    ].filter(Boolean).join(' ');
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 0.93;
    const v = window.speechSynthesis.getVoices().find(v => v.lang === 'en-US') || window.speechSynthesis.getVoices()[0];
    if (v) u.voice = v;
    u.onstart = () => setSpeaking(true);
    u.onend = u.onerror = () => setSpeaking(false);
    window.speechSynthesis.speak(u);
  };

  /* ── regenerate feedback ── */
  const regenerateFeedback = async () => {
    setRegen(true);
    try {
      await api.post(`/interview/${id}/regenerate-feedback`);
      toast.success('Feedback generated!');
      fetchData();   // reload page data
    } catch (err) {
      toast.error(err.response?.data?.message || 'Feedback generation failed');
    } finally {
      setRegen(false);
    }
  };

  /* ── download PDF ── */
  const downloadReport = async () => {
    setGenerating(true);
    try {
      await api.post(`/reports/generate/${id}`);
      const res = await api.get(`/reports/download/${id}`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url; a.download = `interview_report_${id}.pdf`; a.click();
      window.URL.revokeObjectURL(url);
      toast.success('Report downloaded!');
    } catch { toast.error('Failed to generate report'); }
    finally { setGenerating(false); }
  };

  /* ── loading / empty ── */
  if (loading) return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center">
      <div className="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin"/>
    </div>
  );
  if (!data) return null;

  const { interview, result, feedback, qa_review, violations } = data;

  /* ── parse feedback sub-objects safely ── */
  const fb                = feedback || {};
  const strengths         = fb.strengths || [];
  const weaknesses        = fb.weaknesses || [];
  const techGaps          = fb.technical_gaps || [];
  const commAnalysis      = fb.communication_analysis || '';
  const overallSummary    = fb.overall_summary || '';
  const confidenceScore   = fb.confidence_score || 0;

  // resume_suggestions can be object or array (handle both)
  const rs = fb.resume_suggestions || {};
  const resumeGaps        = Array.isArray(rs) ? [] : (rs.resume_gaps || []);
  const resumeImprovements= Array.isArray(rs) ? rs : (rs.resume_improvements || []);
  const focusAreas        = Array.isArray(rs) ? [] : (rs.focus_areas || []);

  // learning_roadmap can be object or array
  const lr = fb.learning_roadmap || {};
  const weeklyPlan        = Array.isArray(lr) ? lr : (lr.weekly_plan || []);
  const learningResources = Array.isArray(lr) ? [] : (lr.learning_resources || []);
  const interviewTips     = Array.isArray(lr) ? [] : (lr.interview_tips || []);

  const hasFeedback = !!(overallSummary || strengths.length || weaknesses.length || techGaps.length);

  const grade = result?.grade || 'F';
  const gradeColor = grade.startsWith('A') ? 'text-emerald-400'
    : grade.startsWith('B') ? 'text-yellow-400' : 'text-red-400';

  const skillData = result?.skill_scores
    ? Object.entries(result.skill_scores)
        .map(([k, v]) => ({ skill: k.length > 12 ? k.slice(0, 12) + '…' : k, score: v.percentage || 0 }))
    : [];

  const tabCls = t => `px-4 py-2 rounded-lg text-sm font-medium transition-all ${
    tab === t ? 'bg-primary-600 text-white' : 'text-slate-400 hover:text-white'
  }`;

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <Navbar/>
      <div className="max-w-5xl mx-auto px-4 sm:px-6 pt-24 pb-16">

        {/* Header */}
        <motion.div initial={{ opacity:0, y:16 }} animate={{ opacity:1, y:0 }} className="mb-8">
          <Link to="/dashboard" className="flex items-center gap-2 text-slate-400 hover:text-white text-sm mb-4">
            <FiArrowLeft size={14}/> Back to Dashboard
          </Link>
          <div className="flex items-start justify-between flex-wrap gap-4">
            <div>
              <h1 className="text-3xl font-display font-bold">Interview Results</h1>
              <p className="text-slate-400 mt-1">
                {interview?.job_role} · {interview?.created_at
                  ? new Date(interview.created_at).toLocaleDateString('en-IN', { day:'numeric', month:'long', year:'numeric' })
                  : ''}
              </p>
            </div>
            <div className="flex items-center gap-3 flex-wrap">
              <button onClick={speakSummary}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium border transition-all ${
                  speaking ? 'bg-yellow-600/20 border-yellow-600/40 text-yellow-300 animate-pulse'
                           : 'bg-slate-800 border-slate-700 text-slate-300 hover:text-white'
                }`}>
                <FiVolume2 size={14}/> {speaking ? 'Stop' : 'Hear Summary'}
              </button>
              <button onClick={downloadReport} disabled={generating}
                className="flex items-center gap-2 bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition-all">
                {generating
                  ? <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"/>
                  : <FiDownload/>}
                {generating ? 'Generating…' : 'Download PDF'}
              </button>
            </div>
          </div>
        </motion.div>

        {/* Score rings */}
        {result && (
          <motion.div initial={{ opacity:0, y:20 }} animate={{ opacity:1, y:0 }} transition={{ delay:0.1 }}
            className="bg-slate-900 border border-slate-800 rounded-2xl p-8 mb-6 flex flex-wrap items-center justify-around gap-6">
            <ScoreRing score={result.technical_percentage} label="Technical"  color="#6366f1"/>
            <div className="text-center">
              <div className={`text-6xl font-display font-bold ${gradeColor}`}>{grade}</div>
              <p className="text-slate-400 text-sm mt-2">Overall Grade</p>
              <p className="text-2xl font-bold text-white mt-1">{(result.overall_percentage || 0).toFixed(1)}%</p>
            </div>
            <ScoreRing score={result.hr_percentage} label="HR Round" color="#10b981"/>
          </motion.div>
        )}

        {/* Tabs */}
        <div className="flex gap-2 mb-6 flex-wrap">
          {['overview','review','feedback','violations'].map(t => (
            <button key={t} onClick={() => setTab(t)} className={tabCls(t)}>
              {t === 'feedback' ? '🎯 Feedback' : t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>

        {/* ══ OVERVIEW ══ */}
        {tab === 'overview' && result && (
          <motion.div initial={{ opacity:0 }} animate={{ opacity:1 }} className="space-y-6">
            {/* Stat chips */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {[
                { label:'Correct',    value:(result.technical_correct||0)+(result.hr_correct||0),    icon:<FiCheckCircle className="text-emerald-400"/>, color:'text-emerald-400' },
                { label:'Wrong',      value:(result.technical_wrong||0)+(result.hr_wrong||0),        icon:<FiXCircle     className="text-red-400"/>,     color:'text-red-400'   },
                { label:'Skipped',    value:(result.technical_skipped||0)+(result.hr_skipped||0),    icon:<FiAlertCircle className="text-yellow-400"/>,   color:'text-yellow-400'},
                { label:'Violations', value:violations?.length||0,                                   icon:<FiAlertCircle className="text-orange-400"/>,   color:'text-orange-400'},
              ].map((s,i)=>(
                <div key={i} className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center gap-3">
                  {s.icon}
                  <div>
                    <p className={`text-xl font-bold ${s.color}`}>{s.value}</p>
                    <p className="text-xs text-slate-400">{s.label}</p>
                  </div>
                </div>
              ))}
            </div>

            {/* Radar */}
            {skillData.length > 2 && (
              <Card title="Skill-wise Performance">
                <ResponsiveContainer width="100%" height={240}>
                  <RadarChart data={skillData}>
                    <PolarGrid stroke="#1e293b"/>
                    <PolarAngleAxis dataKey="skill" tick={{ fill:'#64748b', fontSize:11 }}/>
                    <Radar dataKey="score" stroke="#6366f1" fill="#6366f1" fillOpacity={0.2} strokeWidth={2}/>
                  </RadarChart>
                </ResponsiveContainer>
              </Card>
            )}

            {/* Bar */}
            {skillData.length > 0 && (
              <Card title="Score by Topic">
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={skillData} margin={{ top:5, right:10, left:-20, bottom:5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b"/>
                    <XAxis dataKey="skill" tick={{ fill:'#64748b', fontSize:10 }}/>
                    <YAxis domain={[0,100]} tick={{ fill:'#64748b', fontSize:10 }}/>
                    <Tooltip contentStyle={{ background:'#0f172a', border:'1px solid #1e293b', borderRadius:'8px', color:'#fff' }} formatter={v=>[`${v}%`]}/>
                    <Bar dataKey="score" fill="#6366f1" radius={[4,4,0,0]}/>
                  </BarChart>
                </ResponsiveContainer>
              </Card>
            )}

            {/* Round breakdown */}
            <div className="grid sm:grid-cols-2 gap-4">
              {[
                { label:'Technical Round', correct:result.technical_correct, wrong:result.technical_wrong, skipped:result.technical_skipped, pct:result.technical_percentage, color:'#6366f1' },
                { label:'HR Round',        correct:result.hr_correct,        wrong:result.hr_wrong,        skipped:result.hr_skipped,        pct:result.hr_percentage,        color:'#10b981' },
              ].map((r,i)=>(
                <div key={i} className="bg-slate-900 border border-slate-800 rounded-xl p-5">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="font-medium text-white text-sm">{r.label}</h4>
                    <span className="text-lg font-bold" style={{ color:r.color }}>{(r.pct||0).toFixed(1)}%</span>
                  </div>
                  <div className="w-full h-2 bg-slate-800 rounded-full mb-3">
                    <div className="h-full rounded-full" style={{ width:`${r.pct||0}%`, background:r.color }}/>
                  </div>
                  <div className="flex gap-4 text-xs">
                    <span className="text-emerald-400">✓ {r.correct||0} correct</span>
                    <span className="text-red-400">✗ {r.wrong||0} wrong</span>
                    <span className="text-yellow-400">— {r.skipped||0} skipped</span>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}

        {/* ══ REVIEW ══ */}
        {tab === 'review' && (
          <motion.div initial={{ opacity:0 }} animate={{ opacity:1 }} className="space-y-4">
            {!qa_review?.length && <p className="text-slate-400 text-center py-10">No questions found.</p>}
            {qa_review?.map((q,i)=>(
              <div key={q.id} className={`bg-slate-900 border rounded-xl p-5 ${
                q.is_correct ? 'border-emerald-800/40'
                : q.selected_answer === 'skipped' ? 'border-slate-700'
                : 'border-red-800/40'
              }`}>
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs text-slate-500">Q{i+1}</span>
                    {q.skill_tag && <span className="text-xs bg-slate-800 text-slate-400 px-2 py-0.5 rounded-full">{q.skill_tag}</span>}
                    <span className={`text-xs px-2 py-0.5 rounded-full ${q.question_type==='technical'?'bg-primary-600/20 text-primary-400':'bg-emerald-600/20 text-emerald-400'}`}>
                      {q.question_type}
                    </span>
                  </div>
                  {q.is_correct ? <FiCheckCircle className="text-emerald-400"/>
                    : q.selected_answer==='skipped' ? <FiAlertCircle className="text-yellow-400"/>
                    : <FiXCircle className="text-red-400"/>}
                </div>
                <p className="text-sm text-white mb-3">{q.question_text}</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {['A','B','C','D'].map(opt => {
                    const txt = q[`option_${opt.toLowerCase()}`];
                    const isCorrect  = q.correct_answer === opt;
                    const isSelected = q.selected_answer === opt;
                    return (
                      <div key={opt} className={`text-xs px-3 py-2 rounded-lg border flex items-center gap-2 ${
                        isCorrect ? 'border-emerald-600/50 bg-emerald-600/10 text-emerald-300'
                        : isSelected && !isCorrect ? 'border-red-600/50 bg-red-600/10 text-red-300'
                        : 'border-slate-700 text-slate-400'
                      }`}>
                        <span className="font-bold">{opt}.</span>{txt}
                        {isCorrect && <FiCheckCircle className="ml-auto text-emerald-400 flex-shrink-0" size={12}/>}
                        {isSelected && !isCorrect && <FiXCircle className="ml-auto text-red-400 flex-shrink-0" size={12}/>}
                      </div>
                    );
                  })}
                </div>
                {q.selected_answer==='skipped' && (
                  <p className="text-xs text-yellow-400 mt-2">⏭ Skipped — Correct answer: {q.correct_answer}</p>
                )}
              </div>
            ))}
          </motion.div>
        )}

        {/* ══ FEEDBACK ══ */}
        {tab === 'feedback' && (
          <motion.div initial={{ opacity:0 }} animate={{ opacity:1 }} className="space-y-5">

            {/* No feedback yet */}
            {!hasFeedback ? (
              <div className="text-center py-16">
                <FiStar size={44} className="mx-auto mb-4 text-slate-600"/>
                <p className="text-slate-300 text-lg font-medium mb-2">Feedback not yet generated</p>
                <p className="text-slate-500 text-sm mb-6">This can happen if the AI call failed silently. Click below to generate it now.</p>
                <button onClick={regenerateFeedback} disabled={regen}
                  className="inline-flex items-center gap-2 bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white px-6 py-3 rounded-xl font-medium transition-all">
                  {regen
                    ? <><div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"/>Generating…</>
                    : <><FiRefreshCw size={15}/>Generate Feedback Now</>}
                </button>
              </div>
            ) : (
              <>
                {/* Regenerate button (always available) */}
                <div className="flex justify-end">
                  <button onClick={regenerateFeedback} disabled={regen}
                    className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors">
                    <FiRefreshCw size={12} className={regen ? 'animate-spin' : ''}/>
                    {regen ? 'Regenerating…' : 'Regenerate feedback'}
                  </button>
                </div>

                {/* Overall Summary + readiness */}
                {overallSummary && (
                  <div className="bg-gradient-to-r from-primary-900/40 to-slate-900 border border-primary-700/30 rounded-xl p-6">
                    <h3 className="font-semibold text-white mb-2 flex items-center gap-2">
                      <FiStar className="text-yellow-400"/> Overall Assessment
                    </h3>
                    <p className="text-slate-300 text-sm leading-relaxed">{overallSummary}</p>
                    {confidenceScore > 0 && (
                      <div className="mt-4">
                        <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                          <span>Interview Readiness</span>
                          <span className="font-medium text-white">{Number(confidenceScore).toFixed(0)}%</span>
                        </div>
                        <div className="h-2 bg-slate-800 rounded-full">
                          <div className="h-full rounded-full bg-gradient-to-r from-primary-600 to-primary-400 transition-all"
                            style={{ width:`${Number(confidenceScore)}%` }}/>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Communication */}
                {commAnalysis && (
                  <Card title="💬 Communication & HR Analysis">
                    <p className="text-sm text-slate-300 leading-relaxed">{commAnalysis}</p>
                  </Card>
                )}

                {/* Strengths & Weaknesses */}
                {(strengths.length > 0 || weaknesses.length > 0) && (
                  <div className="grid sm:grid-cols-2 gap-4">
                    {strengths.length > 0 && (
                      <div className="bg-emerald-950/40 border border-emerald-800/30 rounded-xl p-5">
                        <h3 className="font-semibold text-emerald-300 mb-3 flex items-center gap-2 text-sm">
                          <FiCheckCircle size={14}/> What You Did Well
                        </h3>
                        <ul className="space-y-2">
                          {strengths.map((s,i) => (
                            <li key={i} className="text-sm text-emerald-200/80 flex items-start gap-2">
                              <span className="mt-1.5 w-1.5 h-1.5 bg-emerald-400 rounded-full flex-shrink-0"/>
                              {s}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {weaknesses.length > 0 && (
                      <div className="bg-red-950/40 border border-red-800/30 rounded-xl p-5">
                        <h3 className="font-semibold text-red-300 mb-3 flex items-center gap-2 text-sm">
                          <FiXCircle size={14}/> Areas Needing Work
                        </h3>
                        <ul className="space-y-2">
                          {weaknesses.map((w,i) => (
                            <li key={i} className="text-sm text-red-200/80 flex items-start gap-2">
                              <span className="mt-1.5 w-1.5 h-1.5 bg-red-400 rounded-full flex-shrink-0"/>
                              {w}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}

                {/* Technical Gaps */}
                {techGaps.length > 0 && (
                  <Card title="⚠️ Technical Gaps — Topics to Study">
                    <div className="flex flex-wrap gap-2">
                      {techGaps.map((g,i) => (
                        <span key={i} className="text-xs bg-orange-600/20 text-orange-300 px-3 py-1.5 rounded-full border border-orange-600/30 flex items-center gap-1">
                          <FiBook size={11}/>{g}
                        </span>
                      ))}
                    </div>
                  </Card>
                )}

                {/* Focus Areas */}
                {focusAreas.length > 0 && (
                  <Card title="🎯 Priority Focus Areas">
                    <div className="space-y-3">
                      {focusAreas.map((f,i) => (
                        <div key={i} className="flex items-start gap-3 p-3 bg-slate-800 rounded-lg">
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium flex-shrink-0 mt-0.5 ${
                            f.priority==='High' ? 'bg-red-600/30 text-red-300'
                            : f.priority==='Medium' ? 'bg-yellow-600/30 text-yellow-300'
                            : 'bg-green-600/30 text-green-300'
                          }`}>{f.priority||'Medium'}</span>
                          <div>
                            <p className="text-sm font-medium text-white">{f.topic}</p>
                            <p className="text-xs text-slate-400 mt-0.5">{f.reason}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </Card>
                )}

                {/* Resume Gaps */}
                {resumeGaps.length > 0 && (
                  <Card title="📄 Skills Missing From Your Resume">
                    <div className="space-y-3">
                      {resumeGaps.map((g,i) => (
                        <div key={i} className="flex items-start gap-3 p-3 bg-slate-800 rounded-lg">
                          <span className="text-primary-400 mt-0.5 flex-shrink-0 font-bold text-sm">+</span>
                          <div>
                            <p className="text-sm font-medium text-white">{g.skill || g}</p>
                            {g.importance && <p className="text-xs text-slate-400 mt-0.5">{g.importance}</p>}
                          </div>
                        </div>
                      ))}
                    </div>
                  </Card>
                )}

                {/* Resume Improvements */}
                {resumeImprovements.length > 0 && (
                  <Card title="✏️ Resume Improvements">
                    <ul className="space-y-2">
                      {resumeImprovements.map((s,i) => (
                        <li key={i} className="text-sm text-slate-300 flex items-start gap-2">
                          <span className="text-primary-400 mt-0.5 flex-shrink-0">→</span>
                          {typeof s === 'string' ? s : s.suggestion || JSON.stringify(s)}
                        </li>
                      ))}
                    </ul>
                  </Card>
                )}

                {/* Learning Resources */}
                {learningResources.length > 0 && (
                  <Card title="📚 Learning Resources">
                    <div className="space-y-4">
                      {learningResources.map((item,i) => (
                        <div key={i} className="border border-slate-700 rounded-lg p-4">
                          <div className="flex items-center justify-between mb-2">
                            <p className="font-medium text-white text-sm">{item.topic}</p>
                            {item.estimated_time && <span className="text-xs text-slate-500">~{item.estimated_time}</span>}
                          </div>
                          <div className="space-y-1.5">
                            {item.resources?.map((r,j) => (
                              <a key={j} href={r.url} target="_blank" rel="noopener noreferrer"
                                className="flex items-center gap-2 text-xs text-primary-400 hover:text-primary-300 transition-colors">
                                <FiExternalLink size={11}/>{r.name}
                                {r.type && <span className="text-slate-500">({r.type})</span>}
                              </a>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </Card>
                )}

                {/* Weekly Study Plan */}
                {weeklyPlan.length > 0 && (
                  <Card title="🗓️ 4-Week Study Plan">
                    <div className="space-y-4">
                      {weeklyPlan.map((week,i) => (
                        <div key={i} className="border border-slate-700 rounded-lg p-4">
                          <div className="flex items-center gap-3 mb-3">
                            <span className="text-xs bg-primary-600/20 text-primary-300 px-2.5 py-1 rounded-lg font-medium">
                              Week {week.week}
                            </span>
                            <p className="font-medium text-white text-sm">{week.focus}</p>
                          </div>
                          {week.goals?.length > 0 && (
                            <ul className="space-y-1 mb-2">
                              {week.goals.map((g,j) => (
                                <li key={j} className="text-xs text-slate-300 flex items-start gap-1">
                                  <span className="text-emerald-400 flex-shrink-0">✓</span>{g}
                                </li>
                              ))}
                            </ul>
                          )}
                          {week.resources?.length > 0 && (
                            <div className="flex flex-wrap gap-1 mb-2">
                              {week.resources.map((r,j) => (
                                <span key={j} className="text-xs bg-slate-700 text-slate-300 px-2 py-0.5 rounded">{r}</span>
                              ))}
                            </div>
                          )}
                          {week.practice && (
                            <p className="text-xs text-primary-400 flex items-start gap-1">
                              <FiTarget size={11} className="mt-0.5 flex-shrink-0"/>{week.practice}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </Card>
                )}

                {/* Interview Tips */}
                {interviewTips.length > 0 && (
                  <Card title="💡 Tips for Your Next Interview">
                    <ul className="space-y-2">
                      {interviewTips.map((tip,i) => (
                        <li key={i} className="text-sm text-slate-300 flex items-start gap-2">
                          <span className="flex-shrink-0">💡</span>{tip}
                        </li>
                      ))}
                    </ul>
                  </Card>
                )}
              </>
            )}
          </motion.div>
        )}

        {/* ══ VIOLATIONS ══ */}
        {tab === 'violations' && (
          <motion.div initial={{ opacity:0 }} animate={{ opacity:1 }}>
            {!violations?.length ? (
              <div className="text-center py-12 text-slate-400">
                <FiCheckCircle size={40} className="mx-auto mb-3 text-emerald-400"/>
                <p>No violations detected — clean interview!</p>
              </div>
            ) : (
              <div className="space-y-3">
                {violations.map((v,i) => (
                  <div key={i} className="bg-red-950/30 border border-red-800/30 rounded-xl p-4 flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-red-300">
                        {v.type.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase())}
                      </p>
                      <p className="text-xs text-slate-400 mt-0.5">{v.description || '—'}</p>
                    </div>
                    <span className="text-xs text-slate-500">{new Date(v.time).toLocaleTimeString()}</span>
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        )}
      </div>
    </div>
  );
}
