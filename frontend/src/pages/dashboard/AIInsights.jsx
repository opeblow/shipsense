import Card from '../../components/Card';

const INSIGHTS = [
  {
    title: 'Onboarding friction detected',
    text: '63% of users drop off at the API key configuration step. Users who bypass this step have a 78% retention rate vs 22% for those who attempt it.',
    severity: 'high',
  },
  {
    title: 'Power user pattern identified',
    text: 'Users who create 3+ projects in their first week have a 92% retention rate at 30 days. Only 18% of new users reach this threshold.',
    severity: 'medium',
  },
  {
    title: 'Feature adoption gap',
    text: 'The "Export Report" feature is only used by 7% of users, but those who use it have the highest NPS scores. Consider in-app promotion.',
    severity: 'low',
  },
];

export default function AIInsights() {
  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-xl font-semibold text-text">AI Insights</h1>
        <p className="text-sm text-text-secondary mt-1">Patterns ShipSense has detected in your user data</p>
      </div>

      <div className="flex flex-col gap-3">
        {INSIGHTS.map((insight) => (
          <Card key={insight.title}>
            <div className="flex items-start gap-3">
              <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${
                insight.severity === 'high' ? 'bg-error' : insight.severity === 'medium' ? 'bg-warning' : 'bg-success'
              }`} />
              <div>
                <h3 className="text-sm font-semibold text-text mb-1">{insight.title}</h3>
                <p className="text-sm text-text-secondary leading-relaxed">{insight.text}</p>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
