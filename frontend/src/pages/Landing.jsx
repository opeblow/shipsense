import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Button from '../components/Button';
import StatusMessage from '../components/StatusMessage';
import { listProducts } from '../api/client';

const BENEFITS = [
  {
    title: 'Establish an honest baseline.',
    text: 'Start with measured performance, accessibility, structure, and trust signals from your live product.',
  },
  {
    title: 'Add real behavioral evidence.',
    text: 'Connect the ShipSense Event Collector to measure unique users, sessions, actions, and critical-flow completion.',
  },
  {
    title: 'Fix one thing and verify it.',
    text: 'ShipSense turns evidence into one product decision, then measures whether the released change worked.',
  },
];

export default function Landing() {
  const navigate = useNavigate();
  const [url, setUrl] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [latestProductId, setLatestProductId] = useState('');

  useEffect(() => {
    listProducts()
      .then((products) => setLatestProductId(products[0]?.id || ''))
      .catch(() => {});
  }, []);

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
    window.pendo?.track('url_analysis_submitted', {
      url: url.trim(),
      is_valid_url: true,
      analysis_duration_ms: Date.now() - startTime,
    });
    navigate('/onboard', { state: { url: url.trim() } });
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-bg flex flex-col">
      <header className="border-b border-border">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <span className="text-sm font-semibold text-text tracking-tight">ShipSense</span>
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              onClick={() => navigate(latestProductId ? `/dashboard?productId=${latestProductId}` : '/onboard')}
            >
              {latestProductId ? 'Continue workspace' : 'Dashboard'}
            </Button>
            <Button onClick={() => navigate('/onboard')}>Analyze My Product</Button>
          </div>
        </div>
      </header>

      <main className="flex-1 flex flex-col items-center justify-center px-6 py-24">
        <div className="max-w-xl text-center mb-16">
          <h1 className="text-4xl md:text-5xl font-bold text-text leading-tight tracking-tight mb-4">
            Stop shipping fixes you cannot prove.
          </h1>
          <p className="text-lg text-text-secondary leading-relaxed max-w-lg mx-auto">
            ShipSense finds the product issue with the strongest evidence, gives you one clear change, and verifies what happened after release.
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
              {loading ? 'Opening...' : 'Build my baseline'}
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
