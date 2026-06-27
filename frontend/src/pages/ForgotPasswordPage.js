// src/pages/ForgotPasswordPage.js
import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import api from '../services/api';
import { FiMail, FiLock, FiArrowLeft, FiBriefcase, FiEye, FiEyeOff } from 'react-icons/fi';

export default function ForgotPasswordPage() {
  const [step, setStep]               = useState(1);
  const [email, setEmail]             = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirm, setConfirm]         = useState('');
  const [showPwd, setShowPwd]         = useState(false);
  const [loading, setLoading]         = useState(false);
  const [resetData, setResetData]     = useState(null);

  // Step 1 — check email
  const checkEmail = async (e) => {
    e.preventDefault();
    if (!email.trim()) return toast.error('Enter your email');
    setLoading(true);
    try {
      const res = await api.post('/auth/forgot-password', { email: email.trim().toLowerCase() });
      const data = res.data;

      if (!data.found) {
        toast.error('No account found with this email address.');
        return;
      }
      setResetData({ reset_token: data.reset_token, user_id: data.user_id });
      setStep(2);
      toast.success('Email found! Set your new password below.');
    } catch (err) {
      const msg = err.response?.data?.message || 'Error. Please try again.';
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  // Step 2 — reset password
  const resetPassword = async (e) => {
    e.preventDefault();
    if (newPassword !== confirm)  return toast.error('Passwords do not match');
    if (newPassword.length < 8)   return toast.error('Minimum 8 characters');
    const ok = /^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*])/.test(newPassword);
    if (!ok) return toast.error('Need uppercase, lowercase, number & special char (!@#$%^&*)');

    setLoading(true);
    try {
      await api.post('/auth/reset-password', {
        user_id:      resetData.user_id,
        reset_token:  resetData.reset_token,
        new_password: newPassword,
      });
      toast.success('Password changed!');
      setStep(3);
    } catch (err) {
      toast.error(err.response?.data?.message || 'Reset failed. Try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/3 left-1/3 w-96 h-96 bg-primary-600/8 rounded-full blur-3xl"/>
      </div>

      <motion.div initial={{ opacity:0, y:24 }} animate={{ opacity:1, y:0 }}
        className="relative w-full max-w-md">
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-2xl">

          <div className="flex flex-col items-center mb-8">
            <div className="w-12 h-12 bg-gradient-to-br from-primary-500 to-primary-700 rounded-xl flex items-center justify-center mb-3">
              <FiBriefcase className="text-white text-xl"/>
            </div>
            <h1 className="text-2xl font-display font-bold text-white">
              {step === 3 ? 'Password Reset!' : 'Reset Password'}
            </h1>
            <p className="text-slate-400 text-sm mt-1 text-center">
              {step === 1 ? 'Enter your registered email to continue'
               : step === 2 ? 'Create your new password'
               : 'Your password has been updated'}
            </p>
          </div>

          {step === 1 && (
            <form onSubmit={checkEmail} className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Email Address</label>
                <div className="relative">
                  <FiMail className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"/>
                  <input type="email" value={email} onChange={e => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl pl-10 pr-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-primary-500 transition-colors text-sm"/>
                </div>
              </div>
              <button type="submit" disabled={loading}
                className="w-full bg-gradient-to-r from-primary-600 to-primary-700 hover:from-primary-500 disabled:opacity-50 text-white font-semibold py-3 rounded-xl transition-all flex items-center justify-center gap-2">
                {loading
                  ? <><div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"/>Checking...</>
                  : 'Continue'}
              </button>
            </form>
          )}

          {step === 2 && (
            <form onSubmit={resetPassword} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">New Password</label>
                <div className="relative">
                  <FiLock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"/>
                  <input type={showPwd ? 'text' : 'password'}
                    value={newPassword} onChange={e => setNewPassword(e.target.value)}
                    placeholder="Min 8 chars e.g. Test@1234"
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl pl-10 pr-10 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-primary-500 transition-colors text-sm"/>
                  <button type="button" onClick={() => setShowPwd(!showPwd)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300">
                    {showPwd ? <FiEyeOff/> : <FiEye/>}
                  </button>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Confirm Password</label>
                <div className="relative">
                  <FiLock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"/>
                  <input type="password" value={confirm} onChange={e => setConfirm(e.target.value)}
                    placeholder="Repeat new password"
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl pl-10 pr-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-primary-500 transition-colors text-sm"/>
                </div>
              </div>
              <div className="bg-slate-800 rounded-xl p-3 text-xs text-slate-400">
                Must have: 8+ chars, uppercase, lowercase, number, special char (!@#$%^&*)
              </div>
              <button type="submit" disabled={loading}
                className="w-full bg-gradient-to-r from-primary-600 to-primary-700 hover:from-primary-500 disabled:opacity-50 text-white font-semibold py-3 rounded-xl transition-all flex items-center justify-center gap-2">
                {loading
                  ? <><div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"/>Resetting...</>
                  : 'Reset Password'}
              </button>
            </form>
          )}

          {step === 3 && (
            <div className="text-center">
              <div className="text-6xl mb-4">🎉</div>
              <p className="text-slate-300 mb-2 font-medium">Password changed successfully!</p>
              <p className="text-slate-500 text-sm mb-6">You can now login with your new password.</p>
              <Link to="/login"
                className="inline-flex items-center gap-2 bg-primary-600 hover:bg-primary-500 text-white font-semibold px-6 py-3 rounded-xl transition-all">
                Go to Login
              </Link>
            </div>
          )}

          {step < 3 && (
            <Link to="/login" className="mt-5 flex items-center justify-center gap-2 text-sm text-slate-400 hover:text-white transition-colors">
              <FiArrowLeft size={14}/> Back to Login
            </Link>
          )}
        </div>
      </motion.div>
    </div>
  );
}
