// src/pages/RegisterPage.js
import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import { FiUser, FiMail, FiLock, FiEye, FiEyeOff, FiBriefcase, FiRefreshCw } from 'react-icons/fi';

export default function RegisterPage() {
  const { register: registerUser } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading]     = useState(false);
  const [showPwd, setShowPwd]     = useState(false);
  const [step, setStep]           = useState(1);
  const [userId, setUserId]       = useState(null);
  const [userEmail, setUserEmail] = useState('');
  const [otp, setOtp]             = useState('');
  const [verifying, setVerifying] = useState(false);
  const [resending, setResending] = useState(false);

  const { register, handleSubmit, watch, formState: { errors } } = useForm();
  const password = watch('password', '');

  const onSubmit = async (data) => {
    setLoading(true);
    try {
      const res = await registerUser(data);
      setUserId(res.user_id);
      setUserEmail(data.email);
      setStep(2);
      if (res.email_error) {
        toast.error('Account created but email failed. Use Resend OTP button.', { duration: 6000 });
      } else {
        toast.success('OTP sent to your email!');
      }
    } catch (err) {
      const fieldErrors = err.response?.data?.errors || {};
      const msg = err.response?.data?.message || 'Registration failed';
      if (fieldErrors.email) toast.error(fieldErrors.email);
      else toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const verifyOtp = async () => {
    if (otp.length !== 6) return toast.error('Enter the 6-digit OTP');
    setVerifying(true);
    try {
      await api.post('/auth/verify-email', { user_id: userId, otp });
      toast.success('Email verified! You can now login.');
      navigate('/login');
    } catch (err) {
      toast.error(err.response?.data?.message || 'Invalid or expired OTP');
    } finally {
      setVerifying(false);
    }
  };

  const resendOtp = async () => {
    setResending(true);
    try {
      await api.post('/auth/resend-otp', { user_id: userId });
      toast.success('New OTP sent to your email!');
      setOtp('');
    } catch (err) {
      toast.error(err.response?.data?.message || 'Failed to resend OTP');
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/3 right-1/4 w-96 h-96 bg-primary-600/8 rounded-full blur-3xl" />
        <div className="absolute bottom-1/3 left-1/4 w-80 h-80 bg-primary-800/8 rounded-full blur-3xl" />
      </div>

      <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} className="relative w-full max-w-md">
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-2xl">

          {/* Logo */}
          <div className="flex flex-col items-center mb-8">
            <div className="w-12 h-12 bg-gradient-to-br from-primary-500 to-primary-700 rounded-xl flex items-center justify-center mb-3">
              <FiBriefcase className="text-white text-xl" />
            </div>
            <h1 className="text-2xl font-display font-bold text-white">
              {step === 1 ? 'Create Account' : 'Verify Your Email'}
            </h1>
            <p className="text-slate-400 text-sm mt-1 text-center">
              {step === 1 ? 'Start your interview journey today' : `OTP sent to ${userEmail}`}
            </p>
          </div>

          {/* Step 1 — Registration form */}
          {step === 1 && (
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              {/* Full Name */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Full Name</label>
                <div className="relative">
                  <FiUser className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                  <input {...register('full_name', { required: 'Required', minLength: { value: 2, message: 'Min 2 chars' } })}
                    placeholder="John Doe"
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl pl-10 pr-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-primary-500 transition-colors text-sm" />
                </div>
                {errors.full_name && <p className="text-red-400 text-xs mt-1">{errors.full_name.message}</p>}
              </div>

              {/* Email */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Email</label>
                <div className="relative">
                  <FiMail className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                  <input type="email" {...register('email', { required: 'Required' })}
                    placeholder="you@example.com"
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl pl-10 pr-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-primary-500 transition-colors text-sm" />
                </div>
                {errors.email && <p className="text-red-400 text-xs mt-1">{errors.email.message}</p>}
              </div>

              {/* Password */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Password</label>
                <div className="relative">
                  <FiLock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                  <input type={showPwd ? 'text' : 'password'}
                    {...register('password', {
                      required: 'Required',
                      minLength: { value: 8, message: 'Min 8 characters' },
                      pattern: { value: /^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*])/, message: 'Need uppercase, lowercase, number & special char' }
                    })}
                    placeholder="Min 8 chars, e.g. Test@1234"
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl pl-10 pr-10 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-primary-500 transition-colors text-sm" />
                  <button type="button" onClick={() => setShowPwd(!showPwd)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300">
                    {showPwd ? <FiEyeOff /> : <FiEye />}
                  </button>
                </div>
                {errors.password && <p className="text-red-400 text-xs mt-1">{errors.password.message}</p>}
              </div>

              {/* Confirm Password */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Confirm Password</label>
                <div className="relative">
                  <FiLock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                  <input type="password"
                    {...register('confirm_password', {
                      required: 'Please confirm',
                      validate: v => v === password || 'Passwords do not match'
                    })}
                    placeholder="Repeat password"
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl pl-10 pr-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-primary-500 transition-colors text-sm" />
                </div>
                {errors.confirm_password && <p className="text-red-400 text-xs mt-1">{errors.confirm_password.message}</p>}
              </div>

              <button type="submit" disabled={loading}
                className="w-full bg-gradient-to-r from-primary-600 to-primary-700 hover:from-primary-500 disabled:opacity-50 text-white font-semibold py-3 rounded-xl transition-all flex items-center justify-center gap-2 mt-2">
                {loading ? <><div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />Creating...</> : 'Create Account'}
              </button>
            </form>
          )}

          {/* Step 2 — OTP verification */}
          {step === 2 && (
            <div className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5 text-center">Enter 6-digit OTP</label>
                <input
                  value={otp}
                  onChange={e => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  placeholder="· · · · · ·"
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-4 text-white text-center text-3xl tracking-[0.6em] placeholder-slate-600 focus:outline-none focus:border-primary-500 transition-colors"
                />
                <p className="text-xs text-slate-500 text-center mt-2">Check your inbox and spam folder</p>
              </div>

              <button onClick={verifyOtp} disabled={verifying || otp.length < 6}
                className="w-full bg-gradient-to-r from-primary-600 to-primary-700 hover:from-primary-500 disabled:opacity-50 text-white font-semibold py-3 rounded-xl transition-all flex items-center justify-center gap-2">
                {verifying ? <><div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />Verifying...</> : '✓ Verify Email'}
              </button>

              <button onClick={resendOtp} disabled={resending}
                className="w-full flex items-center justify-center gap-2 text-slate-400 hover:text-white text-sm transition-colors py-2 border border-slate-700 rounded-xl hover:border-slate-500">
                {resending ? <div className="w-3 h-3 border border-slate-400 border-t-transparent rounded-full animate-spin" /> : <FiRefreshCw size={13} />}
                {resending ? 'Sending...' : 'Resend OTP'}
              </button>

              <div className="bg-slate-800 rounded-xl p-4 text-xs text-slate-400 space-y-1">
                <p className="font-medium text-slate-300">📧 Didn't receive the OTP?</p>
                <p>• Check your <strong>spam/junk</strong> folder</p>
                <p>• Wait 1–2 minutes then click Resend OTP</p>
                <p>• Make sure <code className="bg-slate-700 px-1 rounded">roniseikh2004@gmail.com</code> is your correct email</p>
              </div>
            </div>
          )}

          <p className="text-center text-sm text-slate-400 mt-6">
            Already have an account?{' '}
            <Link to="/login" className="text-primary-400 hover:text-primary-300 font-medium">Sign in</Link>
          </p>
        </div>
      </motion.div>
    </div>
  );
}
