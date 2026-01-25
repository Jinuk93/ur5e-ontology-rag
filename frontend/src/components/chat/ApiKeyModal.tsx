'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Key, Eye, EyeOff, AlertCircle, CheckCircle } from 'lucide-react';
import { useApiKeyStore } from '@/stores/apiKeyStore';

export function ApiKeyModal() {
  const { showKeyModal, closeKeyModal, setApiKey, apiKey, isKeyRegistered } = useApiKeyStore();
  const [inputKey, setInputKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // 기본적인 API 키 형식 검증 (sk- 로 시작)
    if (!inputKey.trim()) {
      setError('API 키를 입력해주세요.');
      return;
    }

    if (!inputKey.startsWith('sk-')) {
      setError('올바른 OpenAI API 키 형식이 아닙니다. (sk-로 시작해야 합니다)');
      return;
    }

    if (inputKey.length < 20) {
      setError('API 키가 너무 짧습니다.');
      return;
    }

    setApiKey(inputKey);
    setInputKey('');
  };

  const handleClose = () => {
    setInputKey('');
    setError('');
    closeKeyModal();
  };

  const maskedKey = apiKey
    ? `${apiKey.slice(0, 7)}...${apiKey.slice(-4)}`
    : null;

  return (
    <AnimatePresence>
      {showKeyModal && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={handleClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md z-50"
          >
            <div
              className="rounded-xl border border-slate-700/50 shadow-2xl overflow-hidden"
              style={{ backgroundColor: '#0d1320' }}
            >
              {/* Header */}
              <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700/50">
                <div className="flex items-center gap-3">
                  <div
                    className="flex h-9 w-9 items-center justify-center rounded-lg"
                    style={{
                      background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
                      boxShadow: '0 4px 12px rgba(245, 158, 11, 0.3)',
                    }}
                  >
                    <Key className="h-5 w-5 text-white" />
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-white">OpenAI API Key</h2>
                    <p className="text-xs text-slate-400">챗봇 사용을 위해 API 키를 등록하세요</p>
                  </div>
                </div>
                <button
                  onClick={handleClose}
                  className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-700/50 transition-colors"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              {/* Content */}
              <div className="p-5 space-y-4">
                {/* 등록 상태 표시 */}
                {isKeyRegistered && maskedKey && (
                  <div className="flex items-center gap-2 p-3 rounded-lg bg-green-500/10 border border-green-500/30">
                    <CheckCircle className="h-5 w-5 text-green-400 shrink-0" />
                    <div>
                      <p className="text-sm text-green-300 font-medium">API 키가 등록되어 있습니다</p>
                      <p className="text-xs text-green-400/70 font-mono mt-0.5">{maskedKey}</p>
                    </div>
                  </div>
                )}

                {/* 안내 메시지 */}
                <div className="text-sm text-slate-400 space-y-2">
                  <p>
                    OpenAI API 키는{' '}
                    <a
                      href="https://platform.openai.com/api-keys"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-400 hover:text-blue-300 underline"
                    >
                      OpenAI 플랫폼
                    </a>
                    에서 발급받을 수 있습니다.
                  </p>
                  <p className="text-xs text-slate-500">
                    * API 키는 브라우저 로컬 스토리지에 저장됩니다.
                  </p>
                </div>

                {/* 입력 폼 */}
                <form onSubmit={handleSubmit} className="space-y-3">
                  <div className="relative">
                    <input
                      type={showKey ? 'text' : 'password'}
                      value={inputKey}
                      onChange={(e) => {
                        setInputKey(e.target.value);
                        setError('');
                      }}
                      placeholder="sk-..."
                      className="w-full rounded-lg border border-slate-700 bg-slate-800/50 px-4 py-3 pr-12 text-sm text-white placeholder-slate-500 focus:border-amber-500/50 focus:outline-none focus:ring-1 focus:ring-amber-500/50 font-mono"
                    />
                    <button
                      type="button"
                      onClick={() => setShowKey(!showKey)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-white transition-colors"
                    >
                      {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>

                  {/* 에러 메시지 */}
                  {error && (
                    <div className="flex items-center gap-2 text-red-400 text-sm">
                      <AlertCircle className="h-4 w-4 shrink-0" />
                      {error}
                    </div>
                  )}

                  {/* 버튼들 */}
                  <div className="flex gap-2">
                    <button
                      type="submit"
                      disabled={!inputKey.trim()}
                      className="flex-1 py-2.5 rounded-lg text-sm font-medium text-white disabled:opacity-40 disabled:cursor-not-allowed transition-all"
                      style={{
                        background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
                        boxShadow: inputKey.trim()
                          ? '0 4px 12px rgba(245, 158, 11, 0.4)'
                          : 'none',
                      }}
                    >
                      {isKeyRegistered ? 'API 키 변경' : 'API 키 등록'}
                    </button>
                    {isKeyRegistered && (
                      <button
                        type="button"
                        onClick={handleClose}
                        className="px-4 py-2.5 rounded-lg text-sm font-medium text-slate-300 bg-slate-700/50 hover:bg-slate-700 transition-colors"
                      >
                        닫기
                      </button>
                    )}
                  </div>
                </form>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
