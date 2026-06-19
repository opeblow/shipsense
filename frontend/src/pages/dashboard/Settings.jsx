import { useState } from 'react';
import Card from '../../components/Card';
import Button from '../../components/Button';

const API_URL = import.meta.env.VITE_API_URL || 'https://shipsense-knrs.onrender.com';
const SETTINGS_SNIPPET = `<script src="${API_URL}/static/novus.js" data-app-id="YOUR_APP_ID" data-api-url="${API_URL}"></script>`;

export default function Settings() {
  const [copied, setCopied] = useState(false);

  const handleCopySnippet = async () => {
    try {
      await navigator.clipboard.writeText(SETTINGS_SNIPPET);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      pendo.track('settings_snippet_copied', {
        snippet_type: 'novus_tracker',
        copy_success: true,
      });
    } catch {
      // ignore
    }
  };

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-xl font-semibold text-text">Settings</h1>
        <p className="text-sm text-text-secondary mt-1">Manage your ShipSense integration</p>
      </div>

      <Card>
        <h3 className="text-sm font-semibold text-text mb-1">Integration</h3>
        <p className="text-sm text-text-secondary mb-4">Your Novus tracker snippet. Add this to your site to start collecting data.</p>
        <pre className="bg-[#0a0a0a] text-[#e5e5e5] p-4 text-xs overflow-x-auto border border-border mb-4 leading-relaxed">{SETTINGS_SNIPPET}</pre>
        <Button variant="secondary" onClick={handleCopySnippet}>{copied ? 'Copied' : 'Copy snippet'}</Button>
      </Card>

      <Card>
        <h3 className="text-sm font-semibold text-text mb-1">Product URL</h3>
        <p className="text-sm text-text-secondary mb-4">The URL ShipSense monitors for user behavior.</p>
        <p className="text-sm text-text font-medium">https://yourapp.com</p>
      </Card>
    </div>
  );
}
