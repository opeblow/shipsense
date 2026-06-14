import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Landing from './pages/Landing';
import Onboarding from './pages/Onboarding';
import DashboardLayout from './components/DashboardLayout';
import Overview from './pages/dashboard/Overview';
import UserBehavior from './pages/dashboard/UserBehavior';
import AIInsights from './pages/dashboard/AIInsights';
import AskAgent from './pages/dashboard/AskAgent';
import Settings from './pages/dashboard/Settings';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/onboard" element={<Onboarding />} />
        <Route path="/dashboard" element={<DashboardLayout />}>
          <Route index element={<Overview />} />
          <Route path="behavior" element={<UserBehavior />} />
          <Route path="insights" element={<AIInsights />} />
          <Route path="ask" element={<AskAgent />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
