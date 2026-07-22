import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Landing from './pages/Landing'
import Screener from './pages/Screener'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/screener" element={<Screener />} />
      </Routes>
    </BrowserRouter>
  )
}
