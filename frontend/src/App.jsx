import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import WhatsAppGate from './components/WhatsAppGate';
import KioskChat from './components/KioskChat';
import LandingPage from './components/pages/LandingPage';
import LoginPage from './components/pages/LoginPage';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-background">
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/chat" element={<WhatsAppGate />} />
          <Route path="/kiosk" element={<KioskChat />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
