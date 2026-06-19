// src/pages/HomePage.js
import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { FiBriefcase, FiShield, FiTrendingUp, FiFileText, FiArrowRight, FiCheckCircle } from 'react-icons/fi';

const features = [
  { icon: <FiBriefcase />, title: 'AI-Powered Questions', desc: 'Dynamic MCQs generated from your resume, job role, and experience level using Claude AI.' },
  { icon: <FiShield />, title: 'Anti-Cheat System', desc: 'Webcam monitoring, fullscreen lock, tab-switch detection and keyboard shortcut blocking.' },
  { icon: <FiTrendingUp />, title: 'Detailed Analytics', desc: 'Skill-wise radar charts, score trends, grade breakdown and performance comparisons.' },
  { icon: <FiFileText />, title: 'PDF Reports', desc: 'Downloadable PDF report with answers, scores, AI feedback and resume suggestions.' },
];

const steps = [
  'Register & verify your email',
  'Upload your resume (PDF/DOCX)',
  'Enter job role & description',
  'Complete Technical + HR rounds',
  'View results, download PDF report',
];

export default function HomePage() {
  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Nav */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-slate-950/80 backdrop-blur-xl border-b border-slate-800/60 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-primary-700 rounded-lg flex items-center justify-center">
            <FiBriefcase className="text-white text-sm" />
          </div>
          <span className="font-display font-bold text-white text-lg">InterviewAI</span>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/login" className="text-slate-400 hover:text-white text-sm transition-colors px-3 py-2 rounded-lg hover:bg-slate-800">Login</Link>
          <Link to="/register" className="bg-primary-600 hover:bg-primary-500 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors">Get Started</Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative pt-32 pb-24 px-6 text-center overflow-hidden">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-20 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-primary-600/10 rounded-full blur-3xl" />
        </div>
        <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }} className="relative max-w-3xl mx-auto">
          <span className="inline-flex items-center gap-2 text-xs bg-primary-600/20 text-primary-300 px-3 py-1.5 rounded-full border border-primary-600/30 mb-6">
            <span className="w-1.5 h-1.5 bg-primary-400 rounded-full animate-pulse" />
            Powered by Claude AI
          </span>
          <h1 className="text-5xl sm:text-6xl font-display font-bold text-white leading-tight mb-6">
            Ace Your Next<br />
            <span className="bg-gradient-to-r from-primary-400 to-primary-600 bg-clip-text text-transparent">Tech Interview</span>
          </h1>
          <p className="text-lg text-slate-400 mb-10 max-w-xl mx-auto leading-relaxed">
            Practice AI-powered mock interviews tailored to your resume and dream job. Get instant feedback, scores, and personalized improvement roadmaps.
          </p>
          <div className="flex items-center justify-center gap-4 flex-wrap">
            <Link to="/register"
              className="flex items-center gap-2 bg-gradient-to-r from-primary-600 to-primary-700 hover:from-primary-500 text-white font-semibold px-8 py-4 rounded-xl transition-all shadow-lg shadow-primary-900/30 text-base">
              Start Free <FiArrowRight />
            </Link>
            <Link to="/login" className="flex items-center gap-2 text-slate-300 hover:text-white border border-slate-700 hover:border-slate-500 px-8 py-4 rounded-xl transition-all text-base">
              Login
            </Link>
          </div>
        </motion.div>
      </section>

      {/* Features */}
      <section className="py-20 px-6 bg-slate-900/30">
        <div className="max-w-5xl mx-auto">
          <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} className="text-center mb-12">
            <h2 className="text-3xl font-display font-bold text-white">Everything you need to prepare</h2>
            <p className="text-slate-400 mt-3">A complete AI-powered interview practice platform for students.</p>
          </motion.div>
          <div className="grid sm:grid-cols-2 gap-5">
            {features.map((f, i) => (
              <motion.div key={i} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.1 }}
                className="bg-slate-900 border border-slate-800 rounded-2xl p-6 hover:border-primary-800/50 transition-colors">
                <div className="w-10 h-10 bg-primary-600/15 rounded-xl flex items-center justify-center text-primary-400 text-xl mb-4">{f.icon}</div>
                <h3 className="font-semibold text-white mb-2">{f.title}</h3>
                <p className="text-sm text-slate-400 leading-relaxed">{f.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-20 px-6">
        <div className="max-w-3xl mx-auto">
          <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} className="text-center mb-12">
            <h2 className="text-3xl font-display font-bold text-white">How it works</h2>
            <p className="text-slate-400 mt-3">Get interview-ready in 5 simple steps.</p>
          </motion.div>
          <div className="space-y-4">
            {steps.map((step, i) => (
              <motion.div key={i} initial={{ opacity: 0, x: -20 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.08 }}
                className="flex items-center gap-4 bg-slate-900 border border-slate-800 rounded-xl p-4">
                <div className="w-8 h-8 rounded-full bg-primary-600/20 border border-primary-600/30 flex items-center justify-center text-primary-400 text-sm font-bold flex-shrink-0">{i + 1}</div>
                <p className="text-slate-300 text-sm">{step}</p>
                <FiCheckCircle className="ml-auto text-primary-400 flex-shrink-0" size={16} />
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-6">
        <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
          className="max-w-3xl mx-auto bg-gradient-to-br from-primary-900/60 to-primary-800/30 border border-primary-700/30 rounded-3xl p-12 text-center">
          <h2 className="text-3xl font-display font-bold text-white mb-4">Ready to practice?</h2>
          <p className="text-slate-300 mb-8">Join thousands of students preparing smarter with AI-powered mock interviews.</p>
          <Link to="/register" className="inline-flex items-center gap-2 bg-white text-primary-700 font-bold px-8 py-4 rounded-xl hover:bg-primary-50 transition-colors text-base">
            Create Free Account <FiArrowRight />
          </Link>
        </motion.div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800 py-8 px-6 text-center text-slate-500 text-sm">
        <p>© {new Date().getFullYear()} AI Interview Mock Portal. Built with Love By Roni Seikh.</p>
      </footer>
    </div>
  );
}
