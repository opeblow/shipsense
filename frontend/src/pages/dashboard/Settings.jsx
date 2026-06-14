import Card from '../../components/Card';
import Button from '../../components/Button';

export default function Settings() {
  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-xl font-semibold text-text">Settings</h1>
        <p className="text-sm text-text-secondary mt-1">Manage your ShipSense integration</p>
      </div>

      <Card>
        <h3 className="text-sm font-semibold text-text mb-1">Integration</h3>
        <p className="text-sm text-text-secondary mb-4">Your Novus tracker snippet. Add this to your site to start collecting data.</p>
        <pre className="bg-[#0a0a0a] text-[#e5e5e5] p-4 text-xs overflow-x-auto border border-border mb-4 leading-relaxed">{`<script src="https://cdn.shipsense.ai/novus.js" data-app-id="YOUR_APP_ID"></script>`}</pre>
        <Button variant="secondary">Copy snippet</Button>
      </Card>

      <Card>
        <h3 className="text-sm font-semibold text-text mb-1">Product URL</h3>
        <p className="text-sm text-text-secondary mb-4">The URL ShipSense monitors for user behavior.</p>
        <p className="text-sm text-text font-medium">https://yourapp.com</p>
      </Card>
    </div>
  );
}
