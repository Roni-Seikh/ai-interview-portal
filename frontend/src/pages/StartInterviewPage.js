// src/pages/StartInterviewPage.js
import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import Navbar from '../components/common/Navbar';
import api from '../services/api';
import { FiUpload, FiFile, FiX, FiBriefcase, FiUser, FiFileText } from 'react-icons/fi';

const EXPERIENCE_LEVELS = [
  { value: 'fresher', label: 'Fresher (0 years)' },
  { value: 'internship', label: 'Internship Level' },
  { value: '1year', label: '1 Year' },
  { value: '2years', label: '2 Years' },
  { value: '3years', label: '3 Years' },
  { value: '5plus', label: '5+ Years' },
];

export default function StartInterviewPage() {
  const navigate = useNavigate();
  const [resumeFile, setResumeFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [resumeData, setResumeData] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm();

  const handleFileChange = (file) => {
    if (!file) return;
    const ext = file.name.split('.').pop().toLowerCase();
    if (!['pdf', 'docx'].includes(ext)) {
      toast.error('Only PDF and DOCX files allowed');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      toast.error('File must be under 10MB');
      return;
    }
    setResumeFile(file);
    setResumeData(null);
  };

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    handleFileChange(file);
  }, []);

  const uploadResume = async () => {
    if (!resumeFile) return toast.error('Select a resume first');
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('resume', resumeFile);
      const res = await api.post('/resume/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setResumeData(res.data.resume);
      toast.success('Resume parsed successfully!');
    } catch (err) {
      toast.error(err.response?.data?.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const onSubmit = async (data) => {
    if (!resumeData) return toast.error('Please upload your resume first');
    setGenerating(true);
    try {
      const res = await api.post('/interview/setup', {
        resume_id: resumeData.id,
        job_role: data.job_role,
        job_description: data.job_description,
        experience_level: data.experience_level,
      });
      toast.success('Interview ready! Starting now...');
      navigate(`/interview/${res.data.interview_id}`);
    } catch (err) {
      toast.error(err.response?.data?.message || 'Setup failed');
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <Navbar />
      <div className="max-w-3xl mx-auto px-4 sm:px-6 pt-24 pb-16">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <div className="mb-8">
            <h1 className="text-3xl font-display font-bold text-white">Start Mock Interview</h1>
            <p className="text-slate-400 mt-2">Upload your resume and set your preferences to generate personalized questions.</p>
          </div>

          {/* Steps */}
          <div className="flex items-center gap-2 mb-8">
            {['Upload Resume', 'Job Details', 'Start'].map((s, i) => (
              <React.Fragment key={i}>
                <div className={`flex items-center gap-2 text-sm ${resumeData ? 'text-primary-400' : i === 0 ? 'text-white' : 'text-slate-500'}`}>
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                    (i === 0 && resumeData) || (i === 1 && resumeData) ? 'bg-primary-600 text-white' : i === 0 ? 'bg-primary-600 text-white' : 'bg-slate-700 text-slate-400'
                  }`}>{i + 1}</div>
                  <span className="hidden sm:block">{s}</span>
                </div>
                {i < 2 && <div className="flex-1 h-px bg-slate-800" />}
              </React.Fragment>
            ))}
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            {/* Resume Upload */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
              <h2 className="font-semibold text-white mb-4 flex items-center gap-2">
                <FiFile className="text-primary-400" /> Resume Upload
              </h2>

              <div
                onDrop={onDrop}
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                className={`border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer ${
                  dragOver ? 'border-primary-500 bg-primary-500/5' : 'border-slate-700 hover:border-slate-600'
                }`}
                onClick={() => document.getElementById('resume-input').click()}
              >
                <input
                  id="resume-input"
                  type="file"
                  accept=".pdf,.docx"
                  className="hidden"
                  onChange={e => handleFileChange(e.target.files[0])}
                />
                {resumeFile ? (
                  <div className="flex items-center justify-center gap-3">
                    <FiFile className="text-primary-400 text-2xl" />
                    <div className="text-left">
                      <p className="text-white font-medium">{resumeFile.name}</p>
                      <p className="text-slate-400 text-xs">{(resumeFile.size / 1024).toFixed(1)} KB</p>
                    </div>
                    <button
                      type="button"
                      onClick={e => { e.stopPropagation(); setResumeFile(null); setResumeData(null); }}
                      className="text-slate-500 hover:text-red-400 ml-2"
                    >
                      <FiX />
                    </button>
                  </div>
                ) : (
                  <div>
                    <FiUpload className="text-slate-500 text-3xl mx-auto mb-3" />
                    <p className="text-slate-300">Drag & drop or click to upload</p>
                    <p className="text-slate-500 text-xs mt-1">PDF or DOCX, up to 10MB</p>
                  </div>
                )}
              </div>

              {resumeFile && !resumeData && (
                <button
                  type="button"
                  onClick={uploadResume}
                  disabled={uploading}
                  className="mt-3 w-full flex items-center justify-center gap-2 bg-primary-600/20 hover:bg-primary-600/30 border border-primary-600/40 text-primary-300 py-2.5 rounded-xl transition-all text-sm font-medium"
                >
                  {uploading ? <><div className="w-4 h-4 border-2 border-primary-400 border-t-transparent rounded-full animate-spin" />Analyzing...</> : <><FiUpload /> Parse Resume</>}
                </button>
              )}

              {resumeData && (
                <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} className="mt-4 p-4 bg-slate-800 rounded-xl">
                  <p className="text-emerald-400 text-sm font-medium mb-2">✓ Resume parsed successfully</p>
                  {resumeData.extracted_skills?.length > 0 && (
                    <div>
                      <p className="text-xs text-slate-400 mb-1.5">Detected skills:</p>
                      <div className="flex flex-wrap gap-1.5">
                        {resumeData.extracted_skills.slice(0, 12).map((skill, i) => (
                          <span key={i} className="text-xs bg-primary-600/20 text-primary-300 px-2 py-0.5 rounded-full border border-primary-600/30">{skill}</span>
                        ))}
                        {resumeData.extracted_skills.length > 12 && (
                          <span className="text-xs text-slate-500">+{resumeData.extracted_skills.length - 12} more</span>
                        )}
                      </div>
                    </div>
                  )}
                </motion.div>
              )}
            </div>

            {/* Job Details */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
              <h2 className="font-semibold text-white flex items-center gap-2">
                <FiBriefcase className="text-primary-400" /> Job Details
              </h2>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Job Role *</label>
                <input
                  {...register('job_role', { required: 'Job role is required' })}
                  placeholder="e.g. Full Stack Developer, Data Scientist"
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-primary-500 transition-colors text-sm"
                />
                {errors.job_role && <p className="text-red-400 text-xs mt-1">{errors.job_role.message}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Experience Level *</label>
                <select
                  {...register('experience_level', { required: true })}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-primary-500 transition-colors text-sm"
                >
                  {EXPERIENCE_LEVELS.map(l => (
                    <option key={l.value} value={l.value}>{l.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">Job Description *</label>
                <textarea
                  {...register('job_description', { required: 'Job description is required', minLength: { value: 50, message: 'Minimum 50 characters' } })}
                  rows={5}
                  placeholder="Paste the job description here for more targeted questions..."
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-primary-500 transition-colors text-sm resize-none"
                />
                {errors.job_description && <p className="text-red-400 text-xs mt-1">{errors.job_description.message}</p>}
              </div>
            </div>

            {/* Interview Rules */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
              <h2 className="font-semibold text-white mb-3 flex items-center gap-2">
                <FiFileText className="text-yellow-400" /> Interview Rules
              </h2>
              <ul className="space-y-2 text-sm text-slate-400">
                {[
                  '2 rounds: Technical MCQs (15 Qs) + HR MCQs (10 Qs)',
                  '20 seconds per question — answer quickly!',
                  'Camera must stay ON throughout the interview',
                  'Tab switching, right-clicking, and copy/paste are blocked',
                  '3 violations = auto submission',
                  'Interview must be taken in fullscreen mode',
                ].map((rule, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="text-primary-400 mt-0.5">•</span>
                    {rule}
                  </li>
                ))}
              </ul>
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={!resumeData || generating}
              className="w-full bg-gradient-to-r from-primary-600 to-primary-700 hover:from-primary-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold py-4 rounded-xl transition-all flex items-center justify-center gap-2 text-base"
            >
              {generating
                ? <><div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />Generating Questions...</>
                : <><FiBriefcase /> Start Interview</>
              }
            </button>
          </form>
        </motion.div>
      </div>
    </div>
  );
}
