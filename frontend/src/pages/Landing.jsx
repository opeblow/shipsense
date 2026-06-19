import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Button from '../components/Button';
import StatusMessage from '../components/StatusMessage';

const BENEFITS = [
  {
    title: 'Paste your URL. Get instant behavior analysis.',
    text: 'ShipSense crawls your product and identifies how users interact with every screen, button, and flow.',
  },
  {
    title: 'Ask questions about your users in plain English.',
    text: '"Where do people get stuck?" — ShipSense understands natural language and gives you data-driven answers.',
  },
  {
    title: 'Ship the right fix, not the obvious one.',
    text: 'Stop guessing. Every recommendation includes effort level and impact score so you prioritize what matters.',
  },
];

export default function Landing() {
  const navigate = useNavigate();
  const [url, setUrl] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!url.trim()) {
      setError('Enter a URL to analyze');
      return;
    }
    if (!/^https?:\/\/.+/i.test(url.trim())) {
      setError('That doesn\'t look like a valid URL. Start with https://');
      return;
    }
    setError('');
    setLoading(true);
    const startTime = Date.now();
    await new Promise((r) => setTimeout(r, 1200));
    setLoading(false);
    window.pendo?.track('url_analysis_submitted', {
      url: url.trim(),
      is_valid_url: true,
      analysis_duration_ms: Date.now() - startTime,
    });
    navigate('/onboard', { state: { url: url.trim() } });
  };

  return (
    <div className="min-h-screen bg-bg flex flex-col">
      <header className="border-b border-border">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <span className="text-sm font-semibold text-text tracking-tight">ShipSense</span>
          <div className="flex items-center gap-4">
            <Button variant="ghost" onClick={() => navigate('/dashboard')}>Dashboard</Button>
            <Button onClick={() => navigate('/onboard')}>Analyze My Product</Button>
          </div>
        </div>
      </header>

      <main className="flex-1 flex flex-col items-center justify-center px-6 py-24">
        <div className="max-w-xl text-center mb-16">
          <h1 className="text-4xl md:text-5xl font-bold text-text leading-tight tracking-tight mb-4">
            Know what users do. Know what to fix.
          </h1>
          <p className="text-lg text-text-secondary leading-relaxed max-w-lg mx-auto">
            ShipSense is the AI agent that turns user behavior into your next product decision.
          </p>
        </div>

        <div className="w-full max-w-md mb-20">
          <div className="flex gap-2">
            <input
              type="text"
              value={url}
              onChange={(e) => { setUrl(e.target.value); setError(''); }}
              onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
              placeholder="https://yourproduct.com"
              className="flex-1 px-4 py-3 text-sm bg-surface border border-border text-text placeholder:text-text-tertiary outline-none focus:border-accent transition-colors duration-100"
            />
            <Button onClick={handleSubmit} disabled={loading}>
              {loading ? 'Analyzing...' : 'Analyze'}
            </Button>
          </div>
          {error && (
            <div className="mt-2">
              <StatusMessage type="error">{error}</StatusMessage>
            </div>
          )}
        </div>

        <div className="grid md:grid-cols-3 gap-6 max-w-4xl w-full">
          {BENEFITS.map((b) => (
            <div key={b.title} className="bg-surface border border-border p-6">
              <h3 className="text-sm font-semibold text-text mb-2">{b.title}</h3>
              <p className="text-sm text-text-secondary leading-relaxed">{b.text}</p>
            </div>
          ))}
        </div>
      </main>

      <footer className="border-t border-border py-6">
        <div className="max-w-4xl mx-auto px-6 flex items-center justify-between">
          <span className="text-xs text-text-tertiary">&copy; 2026 ShipSense. All rights reserved.</span>
        </div>
      </footer>
    </div>
  );
}
