export const METRICS = {
  activeUsers: { value: '2,847', change: '+12%', label: 'Active Users' },
  avgSession: { value: '4m 32s', change: '-8%', label: 'Avg Session' },
  dropoffRate: { value: '63%', change: '+5%', label: 'Drop-off Rate' },
  topAction: { value: 'Create Project', change: '42%', label: 'Top Action' },
};

export const AI_SUMMARY = {
  text: 'Users are dropping off on step 3 of your onboarding. Most never reach the core feature. The "Create Project" action is your highest engagement point, but 63% of users who start onboarding never complete it. The main friction appears to be the API key configuration step — users who skip it rarely come back.',
  type: 'insight',
};

export const RECOMMENDED_ACTIONS = [
  { id: 1, title: 'Simplify API key configuration step', effort: 'Low', impact: 'High', description: 'Move API key setup to settings, allow users to bypass during onboarding.' },
  { id: 2, title: 'Add progress indicator to onboarding', effort: 'Medium', impact: 'High', description: 'Users need to know how many steps remain. Add a simple step counter.' },
  { id: 3, title: 'Auto-save partial onboarding progress', effort: 'High', impact: 'Medium', description: 'Save state after each step so users can resume without starting over.' },
];

export const BEHAVIOR_DATA = [
  { action: 'Create Project', users: 1247, frequency: '42%', dropoffAfter: '12%' },
  { action: 'Configure API Key', users: 892, frequency: '30%', dropoffAfter: '45%' },
  { action: 'Invite Team Members', users: 534, frequency: '18%', dropoffAfter: '28%' },
  { action: 'View Analytics', users: 421, frequency: '14%', dropoffAfter: '8%' },
  { action: 'Export Report', users: 198, frequency: '7%', dropoffAfter: '3%' },
];

export const BAR_CHART_DATA = [
  { action: 'Create Project', count: 1247 },
  { action: 'Configure Key', count: 892 },
  { action: 'Invite Team', count: 534 },
  { action: 'View Analytics', count: 421 },
  { action: 'Export Report', count: 198 },
];

export const CHAT_HISTORY = [
  { id: 1, question: 'Where are users dropping off?', answer: '63% of users drop off during onboarding, specifically at the API key configuration step (step 3 of 5).', data: '63% drop-off rate on step 3' },
  { id: 2, question: 'What is the most common user action?', answer: '"Create Project" is the most frequent action, performed by 42% of active users. It has the lowest post-action drop-off at 12%.', data: '42% of users create a project' },
];
