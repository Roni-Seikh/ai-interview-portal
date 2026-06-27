// src/pages/ProfilePage.js — Updated: no OTP for password change
import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/common/Navbar';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';
import { FiUser, FiMail, FiPhone, FiLock, FiSave, FiShield, FiEye, FiEyeOff } from 'react-icons/fi';

export default function ProfilePage() {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();
  const [saving, setSaving]         = useState(false);
  const [changingPwd, setChangingPwd] = useState(false);
  const [showNew, setShowNew]       = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  // Profile form
  const { register: regProfile, handleSubmit: handleProfile, formState: { errors: pErrors } } =
    useForm({ defaultValues: { full_name: user?.full_name, phone: user?.phone || '' } });

  // Password form
  const { register: regPwd, handleSubmit: handlePwd, watch, reset: resetPwd,
    formState: { errors: pwdErrors } } = useForm();
  const newPwd = watch('new_password', '');

  const saveProfile = async (data) => {
    setSaving(true);
    try {
      const res = await api.put('/auth/update-profile', data);
      setUser(res.data.user);
      toast.success('Profile updated!');
    } catch (err) {
      toast.error(err.response?.data?.message || 'Update failed');
    } finally {
      setSaving(false);
    }
  };

  // Password change via forgot-password flow (no OTP)
  const changePassword = async (data) => {
    setChangingPwd(true);
    try {
      // Step 1: get reset token for this user's email
      const fpRes = await api.post('/auth/forgot-password', { email: user.email });
      if (!fpRes.data.found) {
        toast.error('Could not verify your account. Try logging out and using Forgot Password.');
        return;
      }

      // Step 2: reset with new password
      await api.post('/auth/reset-password', {
        user_id:      fpRes.data.user_id,
        reset_token:  fpRes.data.reset_token,
        new_password: data.new_password,
      });

      toast.success('Password changed successfully!');
      resetPwd();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Failed to change password');
    } finally {
      setChangingPwd(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <Navbar/>
      <div className="max-w-2xl mx-auto px-4 sm:px-6 pt-24 pb-16">
        <motion.div initial={{ opacity:0, y:16 }} animate={{ opacity:1, y:0 }}>
          <h1 className="text-3xl font-display font-bold text-white mb-8">Profile Settings</h1>

          {/* Avatar card */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 mb-6 flex items-center gap-5">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center text-2xl font-bold text-white flex-shrink-0">
              {user?.full_name?.charAt(0).toUpperCase()}
            </div>
            <div>
              <p className="text-lg font-semibold text-white">{user?.full_name}</p>
              <p className="text-sm text-slate-400">{user?.email}</p>
              <div className="flex items-center gap-2 mt-1">
                <span className={`text-xs px-2 py-0.5 rounded-full ${user?.role === 'admin' ? 'bg-yellow-500/20 text-yellow-300' : 'bg-primary-500/20 text-primary-300'}`}>
                  {user?.role}
                </span>
                <span className="text-xs bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded-full flex items-center gap-1">
                  <FiShield size={10}/> Verified
                </span>
              </div>
            </div>
          </div>

          {/* Profile form */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 mb-6">
            <h2 className="font-semibold text-white mb-5 flex items-center gap-2">
              <FiUser className="text-primary-400"/> Personal Information
            </h2>
            <form onSubmit={handleProfile(saveProfile)} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Full Name</label>
                <div className="relative">
                  <FiUser className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"/>
                  <input {...regProfile('full_name', { required: 'Name required', minLength: { value:2, message:'Min 2 chars' } })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl pl-10 pr-4 py-3 text-white focus:outline-none focus:border-primary-500 transition-colors text-sm"/>
                </div>
                {pErrors.full_name && <p className="text-red-400 text-xs mt-1">{pErrors.full_name.message}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Email</label>
                <div className="relative">
                  <FiMail className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"/>
                  <input value={user?.email} disabled
                    className="w-full bg-slate-800/50 border border-slate-700 rounded-xl pl-10 pr-4 py-3 text-slate-400 text-sm cursor-not-allowed"/>
                </div>
                <p className="text-xs text-slate-500 mt-1">Email cannot be changed</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Phone (optional)</label>
                <div className="relative">
                  <FiPhone className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"/>
                  <input {...regProfile('phone')} placeholder="+91 98765 43210"
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl pl-10 pr-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-primary-500 transition-colors text-sm"/>
                </div>
              </div>

              <button type="submit" disabled={saving}
                className="flex items-center gap-2 bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white font-medium px-5 py-2.5 rounded-xl transition-all text-sm">
                {saving ? <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"/> : <FiSave/>}
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
            </form>
          </div>

          {/* Change Password — no OTP needed */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <h2 className="font-semibold text-white mb-1 flex items-center gap-2">
              <FiLock className="text-yellow-400"/> Change Password
            </h2>
            <p className="text-xs text-slate-400 mb-5">Enter your new password below — no OTP required.</p>

            <form onSubmit={handlePwd(changePassword)} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">New Password</label>
                <div className="relative">
                  <FiLock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"/>
                  <input type={showNew ? 'text' : 'password'}
                    {...regPwd('new_password', {
                      required: 'Password required',
                      minLength: { value: 8, message: 'Min 8 characters' },
                      pattern: { value: /^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*])/, message: 'Need uppercase, lowercase, number & special char' }
                    })}
                    placeholder="New strong password"
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl pl-10 pr-10 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-primary-500 transition-colors text-sm"/>
                  <button type="button" onClick={() => setShowNew(!showNew)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300">
                    {showNew ? <FiEyeOff/> : <FiEye/>}
                  </button>
                </div>
                {pwdErrors.new_password && <p className="text-red-400 text-xs mt-1">{pwdErrors.new_password.message}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Confirm Password</label>
                <div className="relative">
                  <FiLock className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"/>
                  <input type={showConfirm ? 'text' : 'password'}
                    {...regPwd('confirm_password', {
                      required: 'Please confirm',
                      validate: v => v === newPwd || 'Passwords do not match'
                    })}
                    placeholder="Repeat new password"
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl pl-10 pr-10 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-primary-500 transition-colors text-sm"/>
                  <button type="button" onClick={() => setShowConfirm(!showConfirm)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300">
                    {showConfirm ? <FiEyeOff/> : <FiEye/>}
                  </button>
                </div>
                {pwdErrors.confirm_password && <p className="text-red-400 text-xs mt-1">{pwdErrors.confirm_password.message}</p>}
              </div>

              <button type="submit" disabled={changingPwd}
                className="flex items-center gap-2 bg-yellow-600 hover:bg-yellow-500 disabled:opacity-50 text-white font-medium px-5 py-2.5 rounded-xl transition-all text-sm">
                {changingPwd ? <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"/> : <FiLock/>}
                {changingPwd ? 'Updating...' : 'Update Password'}
              </button>
            </form>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
