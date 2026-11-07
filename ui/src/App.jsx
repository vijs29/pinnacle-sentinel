import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Landing from './pages/Landing'
import Screener from './pages/Screener'
import Login from './pages/Login'
import Register from './pages/Register'
import Methodology from './pages/Methodology'
import Watchlist from './pages/Watchlist'
import Infrastructure from './pages/Infrastructure'
import Universe from './pages/Universe';
import PlatformMethodology from './pages/PlatformMethodology';
import ComingSoon from './pages/ComingSoon';
import FlagPage from './pages/FlagPage'
import FlagAnalysis from './pages/FlagAnalysis'
import Beneish from './pages/Beneish'
import Altman from './pages/Altman'
import Scoring from './pages/Scoring'
import Validation from './pages/Validation'
import PlatformIntelligence from './pages/PlatformIntelligence'
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/screener" element={<Screener />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/methodology" element={<Methodology />} />
        <Route path="/watchlist" element={<Watchlist />} />
        <Route path="/infrastructure" element={<Infrastructure />} />
        <Route path="/universe" element={<Universe />} />
        <Route path="/platform-methodology" element={<PlatformMethodology />} />
        <Route path="/portfolios" element={<ComingSoon title="Model Portfolios" description="8 pre-built portfolios from our 126-ticker universe — tracking signal strength, portfolio VaR, and governance risk simultaneously. Live track record updated daily." eta="Q3 2026" />} />
        <Route path="/platform-intelligence" element={<PlatformIntelligence />} />
        <Route path="/validation" element={<Validation />} />
        <Route path="/scoring" element={<Scoring />} />
        <Route path="/flag-analysis" element={<FlagAnalysis />} />
        <Route path="/beneish" element={<Beneish />} />
        <Route path="/altman" element={<Altman />} />
        <Route path="/flags/cfo-resignation" element={<FlagPage flagKey="cfo_resignation" />} />
        <Route path="/flags/material-weakness" element={<FlagPage flagKey="material_weakness" />} />
        <Route path="/flags/auditor-change" element={<FlagPage flagKey="auditor_change" />} />
        <Route path="/flags/late-filing" element={<FlagPage flagKey="late_filing" />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
