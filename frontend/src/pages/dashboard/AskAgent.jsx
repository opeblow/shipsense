import { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import Card from '../../components/Card';
import Loading from '../../components/Loading';
import StatusMessage from '../../components/StatusMessage';
import { askAgent, getAnalystContext } from '../../api/client';


function Citation({ citation }) {
  return (
    <div className="border border-border bg-zebra p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs uppercase tracking-wider text-text-tertiary">
          {citation.source_type.replaceAll('_', ' ')}
        </span>
        {citation.sample_size !== null && citation.sample_size !== undefined && (
          <span className="text-xs text-text-tertiary">
            n={citation.sample_size}
          </span>
        )}
      </div>
      <p className="text-sm font-medium text-text mt-1">{citation.label}</p>
      <p className="text-sm text-accent mt-1">
        {String(citation.value)} {citation.unit !== 'boolean' ? citation.unit : ''}
      </p>
    </div>
  );
}


export default function AskAgent() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const productId = searchParams.get('productId');
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState([]);
  const [analystContext, setAnalystContext] = useState(null);
  const [loadingContext, setLoadingContext] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const inputRef = useRef(null);
  const listRef = useRef(null);
  const [conversationId] = useState(() => crypto.randomUUID());

  useEffect(() => {
    if (!productId) {
      navigate('/onboard', { replace: true });
      return;
    }
    getAnalystContext(productId)
      .then(setAnalystContext)
      .catch((err) => setError(err.response?.data?.detail || 'Failed to load Analyst context'))
      .finally(() => setLoadingContext(false));
    inputRef.current?.focus();
  }, [productId, navigate]);

  useEffect(() => {
    listRef.current?.scrollTo({
      top: listRef.current.scrollHeight,
      behavior: 'smooth',
    });
  }, [messages]);

  const handleAsk = async (suggestedQuestion = '', isSuggested = false) => {
    const question = (suggestedQuestion || query).trim();
    if (!question || loading) return;
    setQuery('');
    setError('');
    setLoading(true);
    const promptMessageId = crypto.randomUUID();

    window.pendo?.trackAgent('prompt', {
      agentId: 'l8vIAIZmKxBHnErFU7JiizOHrMo',
      conversationId,
      messageId: promptMessageId,
      content: question,
      suggestedPrompt: isSuggested,
    });

    try {
      const result = await askAgent(productId, conversationId, question);
      const responseMessageId = crypto.randomUUID();
      setMessages((current) => [
        ...current,
        {
          id: responseMessageId,
          question,
          ...result,
        },
      ]);
      if (result.suggested_questions?.length) {
        setAnalystContext((current) => ({
          ...current,
          suggested_questions: result.suggested_questions,
        }));
      }

      window.pendo?.trackAgent('agent_response', {
        agentId: 'l8vIAIZmKxBHnErFU7JiizOHrMo',
        conversationId,
        messageId: responseMessageId,
        content: result.reply,
      });
      window.pendo?.track('agent_question_asked', {
        query: question.substring(0, 200),
        query_length: question.length,
        response_length: result.reply.length,
        citation_count: result.citations?.length || 0,
        confidence: result.confidence,
        message_count: messages.length + 1,
      });
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to get an Analyst response');
    } finally {
      setLoading(false);
    }
  };

  if (!productId) return null;
  if (loadingContext) return <Loading text="Loading product evidence..." />;

  const suggestions = analystContext?.suggested_questions || [];
  const decision = analystContext?.current_decision;
  const latestExperiment = analystContext?.experiments?.[0];

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px] h-[calc(100vh-4rem)]">
      <div className="flex flex-col min-h-0">
        <div className="mb-6">
          <h1 className="text-xl font-semibold text-text">Analyst</h1>
          <p className="text-sm text-text-secondary mt-1">
            Answers are limited to measured ShipSense evidence and include citations
          </p>
        </div>

        <div ref={listRef} className="flex-1 overflow-y-auto space-y-6 pr-2">
          {messages.length === 0 && !loading && (
            <div className="py-6">
              <p className="text-sm font-medium text-text mb-3">Ask from the current product state</p>
              <div className="grid gap-2 sm:grid-cols-2">
                {suggestions.map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => handleAsk(suggestion, true)}
                    className="text-left text-sm text-text-secondary border border-border bg-surface p-4 hover:border-accent hover:text-text transition-colors cursor-pointer"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((message) => (
            <div key={message.id}>
              <p className="text-sm text-text-secondary mb-2 font-medium">
                {message.question}
              </p>
              <Card className="!p-5">
                <p className="text-sm text-text leading-relaxed">{message.reply}</p>

                {message.citations?.length > 0 && (
                  <div className="mt-5">
                    <p className="text-xs uppercase tracking-wider text-text-tertiary mb-2">
                      Evidence cited
                    </p>
                    <div className="grid gap-2 sm:grid-cols-2">
                      {message.citations.map((citation) => (
                        <Citation key={citation.id} citation={citation} />
                      ))}
                    </div>
                  </div>
                )}

                <div className="mt-5 pt-4 border-t border-border flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-medium text-text">
                      {Math.round(message.confidence * 100)}% evidence confidence
                    </p>
                    <p className="text-xs text-text-tertiary mt-1">
                      {message.confidence_reasons?.join(' ')}
                    </p>
                  </div>
                  {message.follow_up && (
                    <button
                      onClick={() => handleAsk(message.follow_up, true)}
                      className="text-xs text-accent bg-transparent border-none p-0 cursor-pointer hover:underline"
                    >
                      {message.follow_up} →
                    </button>
                  )}
                </div>
              </Card>
            </div>
          ))}

          {loading && <Loading text="Analyst is checking the evidence..." />}
          {error && <StatusMessage type="error">{error}</StatusMessage>}
        </div>

        <div className="border-t border-border pt-4 mt-4">
          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(event) => {
                setQuery(event.target.value);
                setError('');
              }}
              onKeyDown={(event) => event.key === 'Enter' && handleAsk()}
              placeholder="Ask about the decision, evidence, or latest experiment..."
              className="flex-1 py-2.5 text-sm bg-transparent border-b border-border outline-none focus:border-accent transition-colors placeholder:text-text-tertiary text-text"
              disabled={loading}
            />
            <button
              onClick={() => handleAsk()}
              disabled={!query.trim() || loading}
              className="text-sm font-medium text-accent hover:text-accent-hover disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer bg-transparent border-none"
            >
              Ask
            </button>
          </div>
        </div>
      </div>

      <aside className="hidden lg:block border-l border-border pl-6 overflow-y-auto">
        <p className="text-xs uppercase tracking-wider text-text-tertiary mb-4">
          Analyst context
        </p>
        <div className="space-y-4">
          <Card className="!p-4">
            <p className="text-xs text-text-tertiary">Evidence available</p>
            <p className="text-2xl font-semibold text-text mt-1">
              {analystContext?.evidence_count || 0}
            </p>
          </Card>

          {decision && (
            <Card className="!p-4">
              <p className="text-xs text-text-tertiary">Current decision #{decision.version}</p>
              <p className="text-sm font-medium text-text mt-2">{decision.title}</p>
              <p className="text-xs text-text-secondary mt-2">{decision.problem}</p>
            </Card>
          )}

          {latestExperiment && (
            <Card className="!p-4">
              <p className="text-xs text-text-tertiary">Latest experiment</p>
              <p className="text-sm font-medium text-text mt-2">{latestExperiment.name}</p>
              <p className="text-xs text-accent mt-2 uppercase">{latestExperiment.status}</p>
            </Card>
          )}
        </div>
      </aside>
    </div>
  );
}
