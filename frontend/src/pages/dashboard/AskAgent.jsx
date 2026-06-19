import { useState, useEffect, useRef } from 'react';
import Card from '../../components/Card';
import Loading from '../../components/Loading';
import StatusMessage from '../../components/StatusMessage';
import { CHAT_HISTORY } from '../../data/mock';

export default function AskAgent() {
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState(CHAT_HISTORY);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const inputRef = useRef(null);
  const listRef = useRef(null);
  const [conversationId] = useState(() => crypto.randomUUID());

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  const handleAsk = async () => {
    const q = query.trim();
    if (!q) return;
    setQuery('');
    setError('');
    setLoading(true);

    const promptMessageId = crypto.randomUUID();
    window.pendo?.trackAgent("prompt", {
      agentId: "l8vIAIZmKxBHnErFU7JiizOHrMo",
      conversationId,
      messageId: promptMessageId,
      content: q,
      suggestedPrompt: false,
    });

    // Simulate agent response
    await new Promise((r) => setTimeout(r, 1000));

    const responseMessageId = crypto.randomUUID();
    const answer = 'Based on your data, the biggest opportunity is reducing friction in the API key configuration step. Users who complete onboarding see 3x higher 7-day retention.';

    setMessages((prev) => [
      ...prev,
      {
        id: responseMessageId,
        question: q,
        answer,
        data: '42% of users complete onboarding · 63% drop at step 3',
      },
    ]);

    window.pendo?.trackAgent("agent_response", {
      agentId: "l8vIAIZmKxBHnErFU7JiizOHrMo",
      conversationId,
      messageId: responseMessageId,
      content: answer,
    });

    setLoading(false);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-text">Ask Agent</h1>
        <p className="text-sm text-text-secondary mt-1">Ask anything about your users</p>
      </div>

      <div className="flex-1 flex flex-col min-h-0">
        {/* Messages */}
        <div ref={listRef} className="flex-1 overflow-y-auto space-y-4 mb-6 pr-2">
          {messages.length === 0 && !loading && (
            <div className="flex items-center justify-center h-full">
              <p className="text-sm text-text-tertiary">Ask your first question to get started.</p>
            </div>
          )}

          {messages.map((msg) => (
            <div key={msg.id}>
              <p className="text-sm text-text-secondary mb-2 font-medium">{msg.question}</p>
              <Card className="!p-4">
                <p className="text-sm text-text leading-relaxed mb-2">{msg.answer}</p>
                <div className="text-xs text-accent bg-accent/5 px-2 py-1 inline-block">
                  {msg.data}
                </div>
              </Card>
            </div>
          ))}

          {loading && (
            <div className="pl-0">
              <Loading text="Agent is thinking..." />
            </div>
          )}

          {error && <StatusMessage type="error">{error}</StatusMessage>}
        </div>

        {/* Input */}
        <div className="border-t border-border pt-4">
          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => { setQuery(e.target.value); setError(''); }}
              onKeyDown={(e) => e.key === 'Enter' && !loading && handleAsk()}
              placeholder="Ask anything about your users..."
              className="flex-1 py-2.5 text-sm bg-transparent border-b border-border outline-none focus:border-accent transition-colors duration-100 placeholder:text-text-tertiary text-text"
              disabled={loading}
            />
            <button
              onClick={handleAsk}
              disabled={!query.trim() || loading}
              className="text-sm font-medium text-accent hover:text-accent-hover transition-colors duration-100 disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer bg-transparent border-none"
            >
              Ask
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
