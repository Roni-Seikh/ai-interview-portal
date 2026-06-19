// src/pages/InterviewPage.js
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';
import Webcam from 'react-webcam';
import api from '../services/api';
import { FiCameraOff, FiAlertTriangle, FiVolume2, FiVolumeX } from 'react-icons/fi';

const VIOLATION_MAX = 3;

function ViolationWarning({ count, max }) {
  if (count === 0) return null;
  const msgs = ['', 'Warning! Suspicious activity detected.', 'Final warning before auto-submit!', 'Auto-submitting now...'];
  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
      className="fixed top-20 left-1/2 -translate-x-1/2 z-50 bg-red-900 border border-red-500 text-red-100 px-6 py-3 rounded-xl flex items-center gap-3 shadow-xl"
    >
      <FiAlertTriangle className="text-red-400 flex-shrink-0" />
      <span className="font-medium">{msgs[Math.min(count, 3)]}</span>
    </motion.div>
  );
}

// ── AI Voice Helper ───────────────────────────────────────────
function speak(text, onEnd) {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(text);
  utter.rate  = 0.92;
  utter.pitch = 1;
  utter.volume = 1;
  const voices = window.speechSynthesis.getVoices();
  const preferred = voices.find(v => v.lang === 'en-US' && v.name.includes('Google'))
    || voices.find(v => v.lang === 'en-US')
    || voices[0];
  if (preferred) utter.voice = preferred;
  if (onEnd) utter.onend = onEnd;
  window.speechSynthesis.speak(utter);
}

function buildQuestionSpeech(q, index, total) {
  const optionTexts = [
    `Option A: ${q.option_a}`,
    `Option B: ${q.option_b}`,
    `Option C: ${q.option_c}`,
    `Option D: ${q.option_d}`,
  ].join('. ');
  return `Question ${index + 1} of ${total}. ${q.question_text}. ${optionTexts}`;
}

export default function InterviewPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const webcamRef = useRef(null);

  const [round, setRound]               = useState('technical');
  const [questions, setQuestions]       = useState([]);
  const [currentIdx, setCurrentIdx]     = useState(0);
  const [answers, setAnswers]           = useState({});
  const [timeLeft, setTimeLeft]         = useState(20);
  const [loading, setLoading]           = useState(true);
  const [submitting, setSubmitting]     = useState(false);
  const [violationCount, setViolationCount] = useState(0);
  const [showWarning, setShowWarning]   = useState(false);
  const [cameraOn, setCameraOn]         = useState(true);
  const [roundStarted, setRoundStarted] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [voiceReady, setVoiceReady]     = useState(false);

  const timerRef      = useRef(null);
  const answerStart   = useRef(Date.now());
  const violationRef  = useRef(0);
  const roundRef      = useRef('technical');
  const questionsRef  = useRef([]);
  const answersRef    = useRef({});
  const currentIdxRef = useRef(0);

  // Keep refs in sync
  useEffect(() => { roundRef.current = round; }, [round]);
  useEffect(() => { questionsRef.current = questions; }, [questions]);
  useEffect(() => { answersRef.current = answers; }, [answers]);
  useEffect(() => { currentIdxRef.current = currentIdx; }, [currentIdx]);

  // ── Load voices ───────────────────────────────────────────
  useEffect(() => {
    if (window.speechSynthesis) {
      const load = () => { if (window.speechSynthesis.getVoices().length > 0) setVoiceReady(true); };
      window.speechSynthesis.onvoiceschanged = load;
      load();
    }
  }, []);

  // ── Load questions ────────────────────────────────────────
  const loadQuestions = useCallback(async (roundType) => {
    setLoading(true);
    try {
      const res = await api.get(`/interview/${id}/questions/${roundType}`);
      const qs = res.data.questions;
      setQuestions(qs);
      questionsRef.current = qs;
      setCurrentIdx(0);
      currentIdxRef.current = 0;
      setAnswers({});
      answersRef.current = {};
      setTimeLeft(20);
      setRoundStarted(true);
    } catch {
      toast.error('Failed to load questions');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadQuestions('technical');
    enterFullscreen();
    setupAntiCheat();
    return () => {
      cleanupAntiCheat();
      if (timerRef.current) clearInterval(timerRef.current);
      if (window.speechSynthesis) window.speechSynthesis.cancel();
    };
  }, []);

  // ── Speak question when it changes ───────────────────────
  useEffect(() => {
    if (!roundStarted || loading || questions.length === 0 || !voiceEnabled) return;
    const q = questions[currentIdx];
    if (!q) return;

    // Small delay so state settles before speaking
    const t = setTimeout(() => {
      if (voiceEnabled) {
        speak(buildQuestionSpeech(q, currentIdx, questions.length));
      }
    }, 300);
    return () => clearTimeout(t);
  }, [currentIdx, roundStarted, questions, voiceEnabled]);

  // ── Timer per question ────────────────────────────────────
  useEffect(() => {
    if (!roundStarted || loading || questions.length === 0) return;
    answerStart.current = Date.now();
    setTimeLeft(20);
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      setTimeLeft(prev => {
        if (prev <= 1) {
          clearInterval(timerRef.current);
          handleAutoAdvance();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timerRef.current);
  }, [currentIdx, roundStarted, questions.length]);

  const handleAutoAdvance = () => {
    const q = questionsRef.current[currentIdxRef.current];
    if (q && !answersRef.current[q.id]) {
      const updated = { ...answersRef.current, [q.id]: { selected: 'skipped', timeTaken: 20 } };
      setAnswers(updated);
      answersRef.current = updated;
    }
    advanceQuestion();
  };

  const advanceQuestion = useCallback(() => {
    const qs  = questionsRef.current;
    const idx = currentIdxRef.current;
    if (idx < qs.length - 1) {
      setCurrentIdx(idx + 1);
      currentIdxRef.current = idx + 1;
    } else {
      submitRound();
    }
  }, []);

  const selectAnswer = (questionId, option) => {
    if (answersRef.current[questionId]) return;
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    const timeTaken = Math.round((Date.now() - answerStart.current) / 1000);
    const updated = { ...answersRef.current, [questionId]: { selected: option, timeTaken } };
    setAnswers(updated);
    answersRef.current = updated;
    clearInterval(timerRef.current);
    setTimeout(advanceQuestion, 500);
  };

  const submitRound = async () => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    setSubmitting(true);

    const answerPayload = questionsRef.current.map(q => ({
      question_id: q.id,
      selected_answer: answersRef.current[q.id]?.selected || 'skipped',
      time_taken_seconds: answersRef.current[q.id]?.timeTaken || 20,
    }));

    try {
      await api.post(`/interview/${id}/submit-round`, {
        answers: answerPayload,
        round_type: roundRef.current,
      });

      if (roundRef.current === 'technical') {
        toast.success('Technical round done! Starting HR round...');
        if (voiceEnabled) speak('Technical round complete. Starting HR round now.');
        setRound('hr');
        roundRef.current = 'hr';
        setRoundStarted(false);
        await loadQuestions('hr');
      } else {
        await api.post(`/interview/${id}/complete`);
        exitFullscreen();
        if (voiceEnabled) {
          speak('Interview completed. Redirecting to your results.', () => {
            navigate(`/results/${id}`);
          });
        } else {
          toast.success('Interview completed!');
          navigate(`/results/${id}`);
        }
      }
    } catch {
      toast.error('Submission failed. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  // ── Anti-Cheat ────────────────────────────────────────────
  const logViolation = useCallback(async (type, description) => {
    try {
      const res = await api.post(`/interview/${id}/violation`, { violation_type: type, description });
      const count = res.data.violation_count;
      violationRef.current = count;
      setViolationCount(count);
      setShowWarning(true);
      setTimeout(() => setShowWarning(false), 3500);
      if (res.data.auto_submitted) {
        if (window.speechSynthesis) window.speechSynthesis.cancel();
        toast.error('Interview auto-submitted due to violations!');
        exitFullscreen();
        navigate(`/results/${id}`);
      }
    } catch { }
  }, [id, navigate]);

  const handleRightClick  = useCallback((e) => { e.preventDefault(); logViolation('right_click', 'Right click attempted'); }, [logViolation]);
  const handleCopy        = useCallback((e) => { e.preventDefault(); logViolation('copy_attempt', 'Copy attempted'); }, [logViolation]);
  const handlePaste       = useCallback((e) => { e.preventDefault(); logViolation('paste_attempt', 'Paste attempted'); }, [logViolation]);
  const handleVisibility  = useCallback(() => { if (document.hidden) logViolation('tab_switch', 'Tab switched or window minimized'); }, [logViolation]);
  const handleKeyDown     = useCallback((e) => {
    const blocked = e.key === 'F12'
      || (e.ctrlKey && e.shiftKey && ['I','J','C','K'].includes(e.key.toUpperCase()))
      || (e.ctrlKey && ['u','U','a','A','s','S'].includes(e.key))
      || e.key === 'PrintScreen';
    if (blocked) { e.preventDefault(); logViolation('keyboard_shortcut', `Blocked: ${e.key}`); }
  }, [logViolation]);

  const setupAntiCheat = () => {
    document.addEventListener('contextmenu', handleRightClick);
    document.addEventListener('copy', handleCopy);
    document.addEventListener('paste', handlePaste);
    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('visibilitychange', handleVisibility);
  };
  const cleanupAntiCheat = () => {
    document.removeEventListener('contextmenu', handleRightClick);
    document.removeEventListener('copy', handleCopy);
    document.removeEventListener('paste', handlePaste);
    document.removeEventListener('keydown', handleKeyDown);
    document.removeEventListener('visibilitychange', handleVisibility);
  };

  const enterFullscreen = () => document.documentElement.requestFullscreen?.().catch(() => {});
  const exitFullscreen  = () => { if (document.fullscreenElement) document.exitFullscreen?.(); };

  const toggleVoice = () => {
    if (voiceEnabled) { window.speechSynthesis?.cancel(); }
    setVoiceEnabled(v => !v);
    toast(voiceEnabled ? '🔇 Voice turned off' : '🔊 Voice turned on', { duration: 1500 });
  };

  // ── Render ────────────────────────────────────────────────
  const currentQuestion = questions[currentIdx];
  const progress   = questions.length > 0 ? (currentIdx / questions.length) * 100 : 0;
  const timerPct   = (timeLeft / 20) * 100;
  const timerColor = timeLeft > 10 ? '#6366f1' : timeLeft > 5 ? '#f59e0b' : '#ef4444';

  if (loading) return (
    <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center gap-4">
      <div className="w-10 h-10 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
      <p className="text-slate-400 text-sm">
        {round === 'hr' ? 'Preparing HR round...' : 'Generating your personalized questions...'}
      </p>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-950 text-white select-none" onContextMenu={e => e.preventDefault()}>
      <AnimatePresence>
        {showWarning && <ViolationWarning count={violationCount} max={VIOLATION_MAX} />}
      </AnimatePresence>

      {/* ── Top Bar ── */}
      <div className="fixed top-0 left-0 right-0 z-40 bg-slate-900/90 backdrop-blur-xl border-b border-slate-800 px-4 py-3">
        <div className="max-w-5xl mx-auto flex items-center justify-between gap-3">

          {/* Round badge */}
          <span className={`text-xs font-semibold px-3 py-1 rounded-full whitespace-nowrap ${
            round === 'technical' ? 'bg-primary-600/20 text-primary-300' : 'bg-emerald-600/20 text-emerald-300'
          }`}>
            {round === 'technical' ? '⚡ Technical Round' : '💼 HR Round'}
          </span>

          <div className="flex items-center gap-3 ml-auto">
            {/* Q counter */}
            <span className="text-sm text-slate-400 hidden sm:block">
              Q {currentIdx + 1} / {questions.length}
            </span>

            {/* Voice toggle */}
            <button onClick={toggleVoice} title={voiceEnabled ? 'Mute voice' : 'Enable voice'}
              className={`p-2 rounded-lg border transition-all ${voiceEnabled ? 'border-primary-600/40 bg-primary-600/15 text-primary-300' : 'border-slate-700 bg-slate-800 text-slate-500'}`}>
              {voiceEnabled ? <FiVolume2 size={15} /> : <FiVolumeX size={15} />}
            </button>

            {/* Timer ring */}
            <div className="relative w-9 h-9 flex-shrink-0">
              <svg className="w-9 h-9 -rotate-90" viewBox="0 0 36 36">
                <circle cx="18" cy="18" r="15" fill="none" stroke="#1e293b" strokeWidth="3" />
                <circle cx="18" cy="18" r="15" fill="none" stroke={timerColor} strokeWidth="3"
                  strokeDasharray={`${timerPct} 100`} strokeLinecap="round"
                  style={{ transition: 'stroke-dasharray 1s linear, stroke 0.3s' }} />
              </svg>
              <span className="absolute inset-0 flex items-center justify-center text-xs font-bold"
                style={{ color: timerColor }}>{timeLeft}</span>
            </div>

            {/* Webcam thumbnail */}
            <div className={`relative w-12 h-12 rounded-lg overflow-hidden border flex-shrink-0 ${cameraOn ? 'border-emerald-600' : 'border-red-600'}`}>
              {cameraOn ? (
                <Webcam ref={webcamRef} audio={false} width={48} height={48}
                  className="object-cover w-full h-full"
                  onUserMediaError={() => {
                    setCameraOn(false);
                    logViolation('camera_off', 'Camera turned off or access denied');
                  }} />
              ) : (
                <div className="w-full h-full bg-slate-800 flex items-center justify-center">
                  <FiCameraOff className="text-red-400 text-xs" />
                </div>
              )}
            </div>

            {/* Violation count */}
            {violationCount > 0 && (
              <span className="text-xs text-red-400 font-medium whitespace-nowrap">
                {violationCount}/{VIOLATION_MAX} violations
              </span>
            )}
          </div>
        </div>

        {/* Progress bar */}
        <div className="max-w-5xl mx-auto mt-2">
          <div className="h-1 bg-slate-800 rounded-full overflow-hidden">
            <motion.div className="h-full bg-gradient-to-r from-primary-600 to-primary-400 rounded-full"
              style={{ width: `${progress}%` }} transition={{ duration: 0.3 }} />
          </div>
        </div>
      </div>

      {/* ── Question Body ── */}
      <div className="max-w-3xl mx-auto px-4 pt-28 pb-20">
        <AnimatePresence mode="wait">
          {currentQuestion && (
            <motion.div key={currentQuestion.id}
              initial={{ opacity: 0, x: 40 }} animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -40 }} transition={{ duration: 0.22 }}
            >
              {/* Skill tag + voice indicator */}
              <div className="flex items-center gap-2 mb-4 flex-wrap">
                {currentQuestion.skill_tag && (
                  <span className="text-xs text-primary-400 bg-primary-600/10 px-2 py-0.5 rounded-full border border-primary-600/20">
                    {currentQuestion.skill_tag}
                  </span>
                )}
                {voiceEnabled && (
                  <span className="text-xs text-slate-500 flex items-center gap-1 animate-pulse">
                    <FiVolume2 size={11} /> Reading question aloud...
                  </span>
                )}
              </div>

              {/* Question text */}
              <h2 className="text-xl font-semibold text-white mb-8 leading-relaxed">
                <span className="text-slate-500 mr-2">{currentIdx + 1}.</span>
                {currentQuestion.question_text}
              </h2>

              {/* Options */}
              <div className="space-y-3">
                {['A', 'B', 'C', 'D'].map(opt => {
                  const optKey    = `option_${opt.toLowerCase()}`;
                  const selected  = answers[currentQuestion.id]?.selected;
                  const isSelected = selected === opt;
                  const isAnswered = !!selected;

                  return (
                    <motion.button key={opt}
                      whileHover={!isAnswered ? { scale: 1.01 } : {}}
                      whileTap={!isAnswered ? { scale: 0.99 } : {}}
                      onClick={() => !isAnswered && selectAnswer(currentQuestion.id, opt)}
                      disabled={isAnswered}
                      className={`w-full text-left px-5 py-4 rounded-xl border transition-all duration-200 flex items-center gap-3 ${
                        isSelected
                          ? 'border-primary-500 bg-primary-600/20 text-white'
                          : isAnswered
                          ? 'border-slate-800 bg-slate-900/30 text-slate-500 cursor-not-allowed'
                          : 'border-slate-700 bg-slate-900 text-white hover:border-primary-600/50 hover:bg-slate-800 cursor-pointer'
                      }`}
                    >
                      <span className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold flex-shrink-0 transition-colors ${
                        isSelected ? 'bg-primary-600 text-white' : 'bg-slate-800 text-slate-400'
                      }`}>{opt}</span>
                      <span className="text-sm">{currentQuestion[optKey]}</span>
                    </motion.button>
                  );
                })}
              </div>

              {/* Skip button */}
              {!answers[currentQuestion.id] && (
                <button
                  onClick={() => {
                    if (window.speechSynthesis) window.speechSynthesis.cancel();
                    const updated = { ...answersRef.current, [currentQuestion.id]: { selected: 'skipped', timeTaken: 20 - timeLeft } };
                    setAnswers(updated);
                    answersRef.current = updated;
                    clearInterval(timerRef.current);
                    setTimeout(advanceQuestion, 100);
                  }}
                  className="mt-6 text-slate-500 hover:text-slate-300 text-sm transition-colors"
                >
                  Skip question →
                </button>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Manual submit on last question */}
        {currentIdx === questions.length - 1 && answers[currentQuestion?.id] && !submitting && (
          <motion.button initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            onClick={submitRound} disabled={submitting}
            className="mt-8 w-full bg-gradient-to-r from-emerald-600 to-emerald-700 hover:from-emerald-500 disabled:opacity-50 text-white font-semibold py-4 rounded-xl transition-all flex items-center justify-center gap-2 text-base"
          >
            {round === 'technical' ? '✅ Submit Technical Round & Start HR' : '🎉 Submit & See Results'}
          </motion.button>
        )}

        {submitting && (
          <div className="mt-8 flex items-center justify-center gap-3 text-slate-400">
            <div className="w-5 h-5 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
            <span>Submitting answers...</span>
          </div>
        )}
      </div>
    </div>
  );
}
