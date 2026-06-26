// src/pages/RegisterPage.js — Instant registration, no OTP
import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import { useAuth } from '../context/AuthContext';
import { FiUser, FiMail, FiLock, FiEye, FiEyeOff, FiBriefcase } from 'react-icons/fi';

export default function RegisterPage() {
  const navigate  = useNavigate();
  const { setUser } = useAuth();
  const [loading, setLoading]   = useState(false);
  const [showPwd, setShowPwd]   = useState(false);
  const [showCpwd, setShowCpwd] = useState(false);

  const { register, handleSubmit, watch, formState: { errors } } = useForm();
  const password = watch('password', '');

  const onSubmit = async (data) => {
    setLoading(true);
    try {
      // Call API directly (no useAuth.register needed)
      const res = await fetch(
        `${process.env.REACT_APP_API_URL}/auth/register`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        }
      );
      const result = await res.json();

      if (!res.ok) {
        const fieldErrors = result.errors || {};
        if (fieldErrors.email) return toast.error(fieldErrors.email);
        return toast.error(result.message || 'Registration failed');
      }

      // Auto-login with returned tokens
      if (result.access_token) {
        localStorage.setItem('access_token', result.access_token);
        localStorage.setItem('refresh_token', result.refresh_token || '');
        setUser(result.user);
        toast.success('Account created! Welcome to InterviewAI 🎉');
        navigate('/dashboard');
      }
    } catch (err) {
      toast.error('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/3 right-1/4 w-96 h-96 bg-primary-600/8 rounded-full blur-3xl" />
        <div className="absolute bottom-1/3 left-1/4 w-80 h-80 bg-primary-800/8 rounded-full blur-3xl" />
      </div>

      <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }}
        className="relative w-full max-w-md">
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-2xl">

          {/* Logo */}
          <div className="flex flex-col items-center mb-8">
            <div className="w-12 h-12 bg-gradient-to-br from-primary-500 to-primary-700 rounded-xl
                            flex items-center justify-center mb-3">
              <FiBriefcase className="text-white text-xl" />
            </div>
            <h1 className="text-2xl font-display font-bold text-white">Create Account</h1>
            <p className="text-slate-400 text-sm mt-1">Start your interview journey today</p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">

            {/* Full Name */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">Full Name</label>
              <div className="relative">
                <FiUser className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  {...register('full_name', {
                    required: 'Full name is required',
                    minLength: { value: 2, message: 'Minimum 2 characters' }
                  })}
                  placeholder="John Doe"
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl pl-10 pr-4
                             py-3 text-white placeholder-slate-500 focus:outline-none
                             focus:border-primary-500 transition-colors text-sm"
                />
              </div>
              {errors.full_name && (
                <p className="text-red-400 text-xs mt-1">{errors.full_name.message}</p>
              )}
            </div>

            {/* Email */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">Email</label>
              <div className="relative">
                <FiMail className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="email"
                  {...register('email', { required: 'Email is required' })}
                  placeholder="you@example.com"
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl pl-10 pr-4
                             py-3 text-white placeholder-slate-500 focus:outline-none
                             focus:border-primary-500 transition-colors text-sm"
                />
              </div>
              {errors.email && (
                <p className="text-red-400 text-xs mt-1">{errors.email.message}</p>
              )}
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">Password</label>
              <div className="relative">
                <FiLock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type={showPwd ? 'text' : 'password'}
                  {...register('password', {
                    required: 'Password is required',
                    minLength: { value: 8, message: 'Minimum 8 characters' },
                    pattern: {
                      value: /^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*])/,
                      message: 'Need uppercase, lowercase, number & special char'
                    }
                  })}
                  placeholder="Min 8 chars e.g. Test@1234"
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl pl-10 pr-10
                             py-3 text-white placeholder-slate-500 focus:outline-none
                             focus:border-primary-500 transition-colors text-sm"
                />
                <button type="button" onClick={() => setShowPwd(!showPwd)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300">
                  {showPwd ? <FiEyeOff /> : <FiEye />}
                </button>
              </div>
              {errors.password && (
                <p className="text-red-400 text-xs mt-1">{errors.password.message}</p>
              )}
            </div>

            {/* Confirm Password */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">
                Confirm Password
              </label>
              <div className="relative">
                <FiLock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type={showCpwd ? 'text' : 'password'}
                  {...register('confirm_password', {
                    required: 'Please confirm your password',
                    validate: v => v === password || 'Passwords do not match'
                  })}
                  placeholder="Repeat password"
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl pl-10 pr-10
                             py-3 text-white placeholder-slate-500 focus:outline-none
                             focus:border-primary-500 transition-colors text-sm"
                />
                <button type="button" onClick={() => setShowCpwd(!showCpwd)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300">
                  {showCpwd ? <FiEyeOff /> : <FiEye />}
                </button>
              </div>
              {errors.confirm_password && (
                <p className="text-red-400 text-xs mt-1">{errors.confirm_password.message}</p>
              )}
            </div>

            <button type="submit" disabled={loading}
              className="w-full bg-gradient-to-r from-primary-600 to-primary-700
                         hover:from-primary-500 disabled:opacity-50 text-white font-semibold
                         py-3 rounded-xl transition-all flex items-center justify-center gap-2 mt-2">
              {loading
                ? <><div className="w-4 h-4 border-2 border-white border-t-transparent
                                    rounded-full animate-spin"/>Creating account...</>
                : 'Create Account'}
            </button>
          </form>

          <p className="text-center text-sm text-slate-400 mt-6">
            Already have an account?{' '}
            <Link to="/login" className="text-primary-400 hover:text-primary-300 font-medium">
              Sign in
            </Link>
          </p>
        </div>
      </motion.div>
    </div>
  );
}
