import React from 'react'
import { Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import Dashboard from './pages/Dashboard'
import Simulation from './pages/Simulation'
import SecurityOverview from './pages/security/SecurityOverview'
import TrustMonitor from './pages/security/TrustMonitor'
import AttackMonitor from './pages/security/AttackMonitor'
import VerificationAnalytics from './pages/security/VerificationAnalytics'
import Analytics from './pages/Analytics'
import Research from './pages/Research'
import Settings from './pages/Settings'
import PresentationMode from './pages/PresentationMode'
import ProfessionalDashboard from './pages/ProfessionalDashboard'
import ResearchConfiguration from './pages/ResearchConfiguration'
import AnalyticsCharts from './pages/AnalyticsCharts'
import ExportSystem from './pages/ExportSystem'
import ResearchReportGenerator from './pages/ResearchReportGenerator'
import Layout from './layouts/Layout'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/dashboard" element={<ProfessionalDashboard />} />
        <Route path="/dashboard/legacy" element={<Dashboard />} />
        <Route path="/simulation" element={<Simulation />} />
        <Route path="/presentation" element={<PresentationMode />} />
        <Route path="/security" element={<SecurityOverview />} />
        <Route path="/security/trust" element={<TrustMonitor />} />
        <Route path="/security/attacks" element={<AttackMonitor />} />
        <Route path="/security/analytics" element={<VerificationAnalytics />} />
        <Route path="/analytics" element={<AnalyticsCharts />} />
        <Route path="/export" element={<ExportSystem />} />
        <Route path="/research" element={<ResearchConfiguration />} />
        <Route path="/research/report" element={<ResearchReportGenerator />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </Layout>
  )
}
