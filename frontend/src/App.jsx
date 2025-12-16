import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Chat from './components/Chat';
import KioskChat from './components/KioskChat';
import LandingPage from './components/pages/LandingPage';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-background">
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/kiosk" element={<KioskChat />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
