'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Loader2, Bot, User, FileText, Network, ChevronDown, ChevronUp, ExternalLink, HelpCircle, AlertCircle, Lightbulb, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useChatStore, ChatMessage } from '@/stores/chatStore';
import { useUIStore } from '@/stores/uiStore';
import { EvidenceDrawer } from '@/components/evidence/EvidenceDrawer';
import { useChatMutation, usePrefetchEvidence } from '@/hooks/useApi';
import { chatMessage, fadeIn } from '@/lib/animations';
import type { ChatResponse } from '@/types/api';

export function ChatPanel() {
  const [input, setInput] = useState('');
  const [evidenceDrawerOpen, setEvidenceDrawerOpen] = useState(false);
  const [selectedEvidence, setSelectedEvidence] = useState<{ traceId: string; response: ChatResponse } | null>(null);
  const { messages, addMessage, updateMessage, isLoading, setLoading } = useChatStore();
  const { selectedEntity, currentView } = useUIStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);

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
    if (!input.trim() || isLoading) return;

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
    if (!text.trim() || isLoading) return;

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
        {selectedEntity && (
          <Badge variant="outline" className="ml-auto text-xs text-slate-400 border-slate-600">
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

      {/* Input */}
      <form onSubmit={handleSubmit} className="border-t border-slate-700/50 p-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="메시지를 입력하세요..."
            disabled={isLoading}
            className="flex-1 rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="flex h-10 w-10 items-center justify-center rounded-lg disabled:opacity-40 disabled:cursor-not-allowed transition-all"
            style={{
              background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
              boxShadow: '0 4px 12px rgba(59, 130, 246, 0.4), inset 0 1px 0 rgba(255,255,255,0.2), inset 0 -2px 4px rgba(0,0,0,0.2)'
            }}
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin text-white" />
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
