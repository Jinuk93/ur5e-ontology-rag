'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Loader2, Bot, User, FileText, Network, ChevronDown, ChevronUp, ExternalLink, HelpCircle, AlertCircle, Lightbulb, Sparkles, Key, Lock, ListChecks, X, Beaker, Database, Search, Zap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useChatStore, ChatMessage } from '@/stores/chatStore';
import { useUIStore } from '@/stores/uiStore';
import { useApiKeyStore } from '@/stores/apiKeyStore';
import { EvidenceDrawer } from '@/components/evidence/EvidenceDrawer';
import { ApiKeyModal } from '@/components/chat/ApiKeyModal';
import { useChatMutation, usePrefetchEvidence } from '@/hooks/useApi';
import { chatMessage, fadeIn } from '@/lib/animations';
import type { ChatResponse } from '@/types/api';

// 테스트 유형 정의
const TEST_TYPES = {
  ONTOLOGY: {
    label: 'ONTOLOGY',
    color: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
    description: '온톨로지 그래프 기반 관계 추론 테스트',
    details: [
      '엔티티 정의/속성 조회',
      'UR5e ↔ Axia80 관계 탐색',
      '엔티티 간 비교/차이 분석',
    ],
  },
  HYBRID: {
    label: 'HYBRID',
    color: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
    description: '온톨로지 + 실시간 센서값 혼합 분석',
    details: [
      '센서값 → 상태 추론',
      '임계값 기반 경고 판단',
      '패턴 매칭 → 원인 추론',
    ],
  },
  RAG: {
    label: 'RAG',
    color: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    description: '문서/로그 검색 기반 RAG 응답',
    details: [
      '에러코드 → 원인/해결책 검색',
      '패턴 이력 로그 조회',
      '매뉴얼 문서 참조',
    ],
  },
};

// 예시 질문 데이터 - 테스트 유형별 분류
const EXAMPLE_QUESTIONS = {
  ontology: {
    title: '온톨로지 추론',
    icon: Database,
    description: 'UR5e + Axia80 관계 추론',
    testType: 'ONTOLOGY',
    questions: [
      // 엔티티 정의 (5개)
      'Fz가 뭐야?',
      'Tx는 무슨 축이야?',
      'UR5e는 어떤 로봇이야?',
      'Axia80 센서 설명해줘',
      'ControlBox가 뭐야?',
      // UR5e-Axia80 관계 (5개)
      'Axia80은 UR5e의 어디에 장착돼?',
      'ToolFlange에 뭐가 연결되어 있어?',
      'Axia80이 측정하는 축들이 뭐야?',
      'UR5e의 구성요소가 뭐야?',
      'Fz는 어떤 센서가 측정해?',
      // 비교/차이 (4개)
      'Fx와 Fz의 차이가 뭐야?',
      'Tx와 Tz의 차이가 뭐야?',
      '힘 센서와 토크 센서 차이가 뭐야?',
      'Fy와 Ty 중 뭐가 더 민감해?',
      // 상태/속성 (3개)
      'Fz 정상 범위가 어떻게 돼?',
      'Tx 정상 범위가 뭐야?',
      'Joint_0의 가동 범위가 어떻게 돼?',
      // 사양 스펙 (3개)
      'UR5e 페이로드가 몇 kg이야?',
      'Axia80 샘플링 주파수가 얼마야?',
      'UR5e 작업 반경이 얼마야?',
    ],
  },
  sensorAnalysis: {
    title: '센서값 분석',
    icon: Zap,
    description: 'Axia80 실시간 데이터 해석',
    testType: 'HYBRID',
    questions: [
      'Fz가 -350N인데 뭐야?',
      '현재 Fx가 -150N이야. 정상이야?',
      'Tz가 5Nm 넘었는데 문제 있어?',
      'Fy가 -80N인데 위험해?',
      'Tx가 1Nm이면 어떤 상태야?',
      '토크가 갑자기 높아졌어. 뭐가 문제야?',
    ],
  },
  errorResolution: {
    title: '에러 해결',
    icon: HelpCircle,
    description: 'UR5e 에러코드 분석',
    testType: 'RAG',
    questions: [
      'C153 에러 해결법 알려줘',
      'C119 에러가 뭐야?',
      'C189 에러 원인이 뭐야?',
      'C103 에러 어떻게 고쳐?',
      'communication 에러 해결 방법은?',
      'joint position 에러가 자주 나. 왜 그래?',
    ],
  },
  patternHistory: {
    title: '패턴/이력 조회',
    icon: Search,
    description: '센서 패턴 로그 검색',
    testType: 'RAG',
    questions: [
      '최근 충돌 패턴이 있나요?',
      '오늘 이상 패턴이 감지됐어?',
      '과부하 패턴이 발생한 적 있어?',
      '진동 패턴 이력 보여줘',
      '드리프트가 최근에 있었어?',
      '지난 주 에러 패턴 알려줘',
    ],
  },
};

export function ChatPanel() {
  const [input, setInput] = useState('');
  const [showExamples, setShowExamples] = useState(false);
  const [evidenceDrawerOpen, setEvidenceDrawerOpen] = useState(false);
  const [selectedEvidence, setSelectedEvidence] = useState<{ traceId: string; response: ChatResponse } | null>(null);
  const { messages, addMessage, updateMessage, isLoading, setLoading } = useChatStore();
  const { selectedEntity, currentView } = useUIStore();
  const { isKeyRegistered, openKeyModal, initializeFromEnv } = useApiKeyStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // .env.local에서 API 키 로드
  useEffect(() => {
    initializeFromEnv();
  }, [initializeFromEnv]);

  // API 키 미등록 시 챗봇 비활성화
  const isChatDisabled = !isKeyRegistered;

  const chatMutation = useChatMutation();
  const prefetchEvidence = usePrefetchEvidence();

  const handleOpenEvidence = (traceId: string, response: ChatResponse) => {
    prefetchEvidence(traceId);
    setSelectedEvidence({ traceId, response });
    setEvidenceDrawerOpen(true);
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading || isChatDisabled) return;

    const userMessage = input.trim();
    setInput('');

    // Add user message
    addMessage({ role: 'user', content: userMessage });

    // Add assistant placeholder
    const assistantId = addMessage({
      role: 'assistant',
      content: '',
      isLoading: true,
    });

    setLoading(true);

    try {
      const response = await chatMutation.mutateAsync({
        query: userMessage,
        context: {
          selectedEntity: selectedEntity?.id,
          currentValue: selectedEntity?.currentValue,
          currentView,
        },
      });

      if (response.traceId) {
        prefetchEvidence(response.traceId);
      }

      updateMessage(assistantId, {
        content: response.answer,
        response,
        isLoading: false,
      });
    } catch (error) {
      updateMessage(assistantId, {
        content: '죄송합니다. 요청을 처리하는 중 오류가 발생했습니다.',
        error: error instanceof Error ? error.message : '알 수 없는 오류',
        isLoading: false,
      });
    } finally {
      setLoading(false);
    }
  };

  // 예시 질문 클릭 시 바로 전송
  const handleDirectSubmit = async (text: string) => {
    if (!text.trim() || isLoading || isChatDisabled) return;

    const userMessage = text.trim();

    // Add user message
    addMessage({ role: 'user', content: userMessage });

    // Add assistant placeholder
    const assistantId = addMessage({
      role: 'assistant',
      content: '',
      isLoading: true,
    });

    setLoading(true);

    try {
      const response = await chatMutation.mutateAsync({
        query: userMessage,
        context: {
          selectedEntity: selectedEntity?.id,
          currentValue: selectedEntity?.currentValue,
          currentView,
        },
      });

      if (response.traceId) {
        prefetchEvidence(response.traceId);
      }

      updateMessage(assistantId, {
        content: response.answer,
        response,
        isLoading: false,
      });
    } catch (error) {
      updateMessage(assistantId, {
        content: '죄송합니다. 요청을 처리하는 중 오류가 발생했습니다.',
        error: error instanceof Error ? error.message : '알 수 없는 오류',
        isLoading: false,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-full flex-col" style={{ backgroundColor: '#0a0f1a' }}>
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-slate-700/50 px-4 py-3" style={{ backgroundColor: '#0d1320' }}>
        <div
          className="relative flex h-7 w-7 items-center justify-center rounded-lg"
          style={{
            background: 'linear-gradient(135deg, #3b82f6 0%, #06b6d4 100%)',
            boxShadow: '0 4px 12px rgba(59, 130, 246, 0.4), inset 0 1px 0 rgba(255,255,255,0.2), inset 0 -1px 2px rgba(0,0,0,0.2)'
          }}
        >
          <Sparkles className="h-4 w-4 text-white drop-shadow-sm" />
        </div>
        <span className="font-semibold text-white">AI Assistant</span>

        {/* API Key 등록 버튼 */}
        <button
          onClick={openKeyModal}
          className={`ml-auto flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
            isKeyRegistered
              ? 'bg-green-500/20 text-green-400 hover:bg-green-500/30 border border-green-500/30'
              : 'bg-amber-500/20 text-amber-400 hover:bg-amber-500/30 border border-amber-500/30'
          }`}
        >
          <Key className="h-3.5 w-3.5" />
          {isKeyRegistered ? 'API Key' : 'API Key 등록'}
        </button>

        {selectedEntity && (
          <Badge variant="outline" className="text-xs text-slate-400 border-slate-600">
            {selectedEntity.name} 선택됨
          </Badge>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-auto p-4 space-y-4">
        <AnimatePresence mode="popLayout">
          {messages.length === 0 && (
            <motion.div
              key="empty-state"
              initial="hidden"
              animate="visible"
              exit="exit"
              variants={fadeIn}
              className="flex flex-col items-center justify-center h-full text-center"
            >
              <Bot className="h-12 w-12 text-slate-600 mb-3" />
              <p className="text-slate-300 text-base font-semibold">
                &ldquo;UR5e 로봇과 센서에 대해 질문하세요.
              </p>
              <p className="text-slate-300 text-base font-semibold mt-1">
                아래는 질문 예시입니다. 클릭하세요.&rdquo;
              </p>
              <div className="mt-4 space-y-2">
                <SuggestedQuestion text="&quot;현재 Fz가 -350N인데, 무슨 의미인가요?&quot;" onClick={handleDirectSubmit} />
                <SuggestedQuestion text="&quot;C153 에러가 발생했어요. 어떻게 해결하나요?&quot;" onClick={handleDirectSubmit} />
                <SuggestedQuestion text="&quot;최근 충돌 패턴이 있나요?&quot;" onClick={handleDirectSubmit} />
                <SuggestedQuestion text="&quot;조인트 토크가 높을 때 어떻게 대처하나요?&quot;" onClick={handleDirectSubmit} />
                <SuggestedQuestion text="&quot;Axia80 센서의 정상 범위가 어떻게 되나요?&quot;" onClick={handleDirectSubmit} />
              </div>
            </motion.div>
          )}

          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial="hidden"
              animate="visible"
              exit="exit"
              variants={chatMessage}
              layout
            >
              <MessageBubble message={msg} onOpenEvidence={handleOpenEvidence} onSuggestedQuestion={handleDirectSubmit} />
            </motion.div>
          ))}
        </AnimatePresence>
        <div ref={messagesEndRef} />
      </div>

      {/* Example Questions Panel */}
      <AnimatePresence>
        {showExamples && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="border-t border-slate-700/50 overflow-hidden"
          >
            <ExampleQuestionsPanel
              onSelect={(q) => {
                handleDirectSubmit(q);
                setShowExamples(false);
              }}
              onClose={() => setShowExamples(false)}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Input */}
      <form onSubmit={handleSubmit} className="border-t border-slate-700/50 p-4">
        {/* API 키 미등록 시 경고 메시지 */}
        {isChatDisabled && (
          <div className="flex items-center gap-2 mb-3 p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/30">
            <Lock className="h-4 w-4 text-amber-400 shrink-0" />
            <p className="text-xs text-amber-300">
              챗봇을 사용하려면{' '}
              <button
                type="button"
                onClick={openKeyModal}
                className="underline hover:text-amber-200 font-medium"
              >
                OpenAI API Key를 등록
              </button>
              해주세요.
            </p>
          </div>
        )}
        <div className="flex gap-2">
          {/* 예시 질문 토글 버튼 - 눈에 띄는 그라데이션 스타일 */}
          <button
            type="button"
            onClick={() => setShowExamples(!showExamples)}
            className={`flex h-10 items-center gap-1.5 px-3 rounded-lg border transition-all ${
              showExamples
                ? 'bg-gradient-to-r from-cyan-500/30 to-blue-500/30 border-cyan-400/60 text-cyan-300 shadow-[0_0_12px_rgba(34,211,238,0.25)]'
                : 'bg-gradient-to-r from-slate-700/80 to-slate-800/80 border-slate-600 text-slate-300 hover:from-cyan-600/20 hover:to-blue-600/20 hover:border-cyan-500/40 hover:text-cyan-400'
            }`}
            title="예시 질문 보기"
          >
            <ListChecks className="h-4 w-4" />
            <span className="text-xs font-medium whitespace-nowrap">질문 예시</span>
          </button>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={isChatDisabled ? "API Key를 먼저 등록해주세요..." : "메시지를 입력하세요..."}
            disabled={isLoading || isChatDisabled}
            className="flex-1 rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim() || isChatDisabled}
            className="flex h-10 w-10 items-center justify-center rounded-lg disabled:opacity-40 disabled:cursor-not-allowed transition-all"
            style={{
              background: isChatDisabled
                ? 'linear-gradient(135deg, #475569 0%, #334155 100%)'
                : 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
              boxShadow: isChatDisabled
                ? 'none'
                : '0 4px 12px rgba(59, 130, 246, 0.4), inset 0 1px 0 rgba(255,255,255,0.2), inset 0 -2px 4px rgba(0,0,0,0.2)'
            }}
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin text-white" />
            ) : isChatDisabled ? (
              <Lock className="h-4 w-4 text-slate-400" />
            ) : (
              <Send className="h-4 w-4 text-white" />
            )}
          </button>
        </div>
      </form>

      {/* Evidence Drawer */}
      <EvidenceDrawer
        open={evidenceDrawerOpen}
        onOpenChange={setEvidenceDrawerOpen}
        traceId={selectedEvidence?.traceId ?? null}
        response={selectedEvidence?.response}
      />

      {/* API Key Modal */}
      <ApiKeyModal />
    </div>
  );
}

function SuggestedQuestion({
  text,
  onClick,
}: {
  text: string;
  onClick: (text: string) => void;
}) {
  return (
    <button
      onClick={() => onClick(text)}
      className="block w-full text-left text-xs text-slate-500 hover:text-blue-400 transition-colors px-3 py-1.5 rounded-lg hover:bg-slate-800/50"
    >
      &ldquo;{text}&rdquo;
    </button>
  );
}

function MessageBubble({
  message,
  onOpenEvidence,
  onSuggestedQuestion,
}: {
  message: ChatMessage;
  onOpenEvidence: (traceId: string, response: ChatResponse) => void;
  onSuggestedQuestion: (text: string) => void;
}) {
  const [showEvidence, setShowEvidence] = useState(false);
  const isUser = message.role === 'user';

  return (
    <div className={`flex gap-3 ${isUser ? 'justify-end' : ''}`}>
      {!isUser && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-500/20">
          <Bot className="h-4 w-4 text-blue-400" />
        </div>
      )}

      <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} max-w-[85%]`}>
        <Card
          className={`px-3 py-2 ${
            isUser
              ? 'bg-blue-600 text-white border-blue-500'
              : 'bg-slate-800/50 text-slate-100 border-slate-700/50'
          }`}
        >
          {message.isLoading ? (
            <div className="flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span className="text-sm">생각 중...</span>
            </div>
          ) : message.response?.abstain ? (
            <AbstainMessage response={message.response} onSuggestedClick={onSuggestedQuestion} />
          ) : (
            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
          )}
        </Card>

        {/* Response metadata */}
        {!isUser && message.response && !message.isLoading && (
          <ResponseMeta
            response={message.response}
            showEvidence={showEvidence}
            onToggleEvidence={() => setShowEvidence(!showEvidence)}
            onOpenDrawer={() => message.response && onOpenEvidence(message.response.traceId, message.response)}
          />
        )}

        {/* Error display */}
        {message.error && (
          <span className="mt-1 text-xs text-red-400">Error: {message.error}</span>
        )}
      </div>

      {isUser && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-700">
          <User className="h-4 w-4 text-slate-300" />
        </div>
      )}
    </div>
  );
}

function ResponseMeta({
  response,
  showEvidence,
  onToggleEvidence,
  onOpenDrawer,
}: {
  response: ChatResponse;
  showEvidence: boolean;
  onToggleEvidence: () => void;
  onOpenDrawer: () => void;
}) {
  const hasEvidence =
    (response.evidence?.ontologyPathObjects?.length ?? 0) > 0 ||
    (response.evidence?.documentRefs?.length ?? 0) > 0;
  const hasGraph = (response.graph?.nodes?.length ?? 0) > 0;

  return (
    <div className="mt-2 space-y-2">
      {/* Meta badges */}
      <div className="flex flex-wrap gap-1">
        <Badge variant="outline" className="text-xs text-slate-500 border-slate-700">
          {response.queryType}
        </Badge>
        {response.reasoning?.confidence !== undefined && (
          <Badge variant="outline" className="text-xs text-slate-500 border-slate-700">
            신뢰도 {Math.round(response.reasoning.confidence * 100)}%
          </Badge>
        )}
        {response.traceId && (
          <Badge variant="outline" className="text-xs text-slate-600 border-slate-700 font-mono">
            {response.traceId.slice(0, 8)}
          </Badge>
        )}
      </div>

      {/* Evidence toggle */}
      {(hasEvidence || hasGraph) && (
        <div className="flex items-center gap-3">
          <button
            onClick={onToggleEvidence}
            className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors"
          >
            {showEvidence ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            근거 {showEvidence ? '숨기기' : '보기'}
          </button>
          <button
            onClick={onOpenDrawer}
            className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300 transition-colors"
          >
            <ExternalLink className="h-3 w-3" />
            상세
          </button>
        </div>
      )}

      {/* Evidence details */}
      {showEvidence && (
        <Card className="p-3 bg-slate-900/50 border-slate-700/50 space-y-3">
          {/* Ontology paths */}
          {response.evidence?.ontologyPathObjects &&
            response.evidence.ontologyPathObjects.length > 0 && (
              <div>
                <div className="flex items-center gap-1 text-xs text-slate-400 mb-1">
                  <Network className="h-3 w-3" />
                  온톨로지 경로
                </div>
                {response.evidence.ontologyPathObjects.map((p, i) => (
                  <div key={i} className="text-xs text-slate-300 font-mono bg-slate-800/50 px-2 py-1 rounded mt-1">
                    {p.path.join(' → ')}
                  </div>
                ))}
              </div>
            )}

          {/* Document refs */}
          {response.evidence?.documentRefs &&
            response.evidence.documentRefs.length > 0 && (
              <div>
                <div className="flex items-center gap-1 text-xs text-slate-400 mb-1">
                  <FileText className="h-3 w-3" />
                  문서 참조
                </div>
                {response.evidence.documentRefs.map((d, i) => (
                  <div key={i} className="text-xs text-slate-300">
                    {d.docId}
                    {d.page && ` (p.${d.page})`}
                    {d.relevance !== undefined && (
                      <span className="text-slate-500 ml-1">
                        관련도 {Math.round(d.relevance * 100)}%
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}

          {/* Graph summary */}
          {hasGraph && (
            <div>
              <div className="flex items-center gap-1 text-xs text-slate-400 mb-1">
                <Network className="h-3 w-3" />
                그래프
              </div>
              <div className="text-xs text-slate-300">
                노드 {response.graph?.nodes.length}개, 엣지 {response.graph?.edges.length}개
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}

function AbstainMessage({
  response,
  onSuggestedClick,
}: {
  response: ChatResponse;
  onSuggestedClick: (text: string) => void;
}) {
  return (
    <div className="space-y-3">
      {/* Main abstain message */}
      <div className="flex items-start gap-2">
        <HelpCircle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
        <div>
          <p className="text-sm font-medium text-amber-300">
            신뢰할 수 있는 답변을 제공하기 어렵습니다.
          </p>
          {response.abstainReason && (
            <p className="text-xs text-slate-400 mt-1">
              {response.abstainReason}
            </p>
          )}
        </div>
      </div>

      {/* Partial evidence - what's missing */}
      {response.partialEvidence && (
        <div className="bg-slate-900/50 rounded-lg p-3 space-y-2">
          {response.partialEvidence.found.length > 0 && (
            <div>
              <div className="flex items-center gap-1 text-xs text-green-400 mb-1">
                <AlertCircle className="h-3 w-3" />
                찾은 정보
              </div>
              <ul className="text-xs text-slate-300 space-y-0.5 ml-4">
                {response.partialEvidence.found.map((item, i) => (
                  <li key={i}>• {item}</li>
                ))}
              </ul>
            </div>
          )}
          {response.partialEvidence.missing.length > 0 && (
            <div>
              <div className="flex items-center gap-1 text-xs text-amber-400 mb-1">
                <AlertCircle className="h-3 w-3" />
                부족한 정보
              </div>
              <ul className="text-xs text-slate-300 space-y-0.5 ml-4">
                {response.partialEvidence.missing.map((item, i) => (
                  <li key={i}>• {item}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Suggested questions */}
      {response.suggestedQuestions && response.suggestedQuestions.length > 0 && (
        <div className="space-y-1.5">
          <div className="flex items-center gap-1 text-xs text-blue-400">
            <Lightbulb className="h-3 w-3" />
            이렇게 질문해 보세요
          </div>
          <div className="space-y-1">
            {response.suggestedQuestions.map((question, i) => (
              <button
                key={i}
                onClick={() => onSuggestedClick(question)}
                className="block w-full text-left text-xs text-slate-400 hover:text-blue-400 transition-colors px-2 py-1.5 rounded bg-slate-800/50 hover:bg-slate-700/50"
              >
                &ldquo;{question}&rdquo;
              </button>
            ))}
          </div>
        </div>
      )}

      {/* If there's still an answer, show it */}
      {response.answer && response.answer.trim() !== '' && (
        <div className="border-t border-slate-700/50 pt-2 mt-2">
          <p className="text-xs text-slate-400 mb-1">참고 정보:</p>
          <p className="text-sm text-slate-300 whitespace-pre-wrap">{response.answer}</p>
        </div>
      )}
    </div>
  );
}

// 예시 질문 패널 컴포넌트 - 개발자 테스트용
function ExampleQuestionsPanel({
  onSelect,
  onClose,
}: {
  onSelect: (question: string) => void;
  onClose: () => void;
}) {
  const [selectedTestType, setSelectedTestType] = useState<keyof typeof TEST_TYPES | null>(null);
  const categories = Object.entries(EXAMPLE_QUESTIONS);
  const testTypes = Object.entries(TEST_TYPES) as [keyof typeof TEST_TYPES, typeof TEST_TYPES[keyof typeof TEST_TYPES]][];

  // 선택된 테스트 유형에 맞는 카테고리만 필터링
  const filteredCategories = selectedTestType
    ? categories.filter(([, cat]) => cat.testType === selectedTestType)
    : categories;

  const totalQuestions = selectedTestType
    ? filteredCategories.reduce((acc, [, cat]) => acc + cat.questions.length, 0)
    : categories.reduce((acc, [, cat]) => acc + cat.questions.length, 0);

  return (
    <div className="p-4 bg-slate-900/80 max-h-[500px] overflow-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <ListChecks className="h-4 w-4 text-cyan-400" />
            <span className="text-sm font-medium text-white">질문지 예시</span>
          </div>
          <span className="text-[10px] text-slate-500 bg-slate-800 px-2 py-0.5 rounded">
            개발자 테스트용 · {totalQuestions}개
          </span>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Test Type Selection - Compact 2-Column Grid */}
      <div className="mb-3 space-y-1.5">
        <span className="text-[10px] text-slate-500 font-medium">테스트 유형 필터</span>
        <div className="grid grid-cols-3 gap-1.5">
          {testTypes.map(([typeKey, typeInfo]) => {
            const isSelected = selectedTestType === typeKey;
            return (
              <button
                key={typeKey}
                onClick={() => setSelectedTestType(isSelected ? null : typeKey)}
                className={`flex flex-col items-start gap-1 p-2 rounded-lg border text-left transition-all ${
                  isSelected
                    ? `${typeInfo.color} border-current`
                    : 'bg-slate-800/50 border-slate-700/50 hover:border-slate-600'
                }`}
              >
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${typeInfo.color}`}>
                  {typeInfo.label}
                </span>
                <p className={`text-[10px] leading-tight ${isSelected ? 'opacity-90' : 'text-slate-400'}`}>
                  {typeInfo.description}
                </p>
              </button>
            );
          })}
        </div>
      </div>

      {/* Divider */}
      <div className="border-t border-slate-700/50 my-3" />

      {/* Questions List - Grouped by Category */}
      <div className="space-y-4">
        {filteredCategories.map(([key, category]) => {
          const Icon = category.icon;
          return (
            <div key={key} className="space-y-2">
              {/* Category Header - No Badge */}
              <div className="flex items-center gap-2 text-xs py-1">
                <Icon className="h-3.5 w-3.5 text-slate-400" />
                <span className="text-slate-300 font-medium">{category.title}</span>
                <span className="text-[10px] text-slate-500">· {category.description}</span>
                <span className="text-[10px] text-slate-600 ml-auto">{category.questions.length}개</span>
              </div>
              {/* Questions Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-1">
                {category.questions.map((question, idx) => (
                  <button
                    key={idx}
                    onClick={() => onSelect(question)}
                    className="text-left text-xs text-slate-300 hover:text-cyan-400 px-2 py-1.5 rounded bg-slate-800/30 hover:bg-slate-700/50 transition-colors truncate"
                    title={question}
                  >
                    &ldquo;{question}&rdquo;
                  </button>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
