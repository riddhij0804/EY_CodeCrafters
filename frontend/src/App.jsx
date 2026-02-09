import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { CartProvider } from '@/contexts/CartContext.jsx';
import MainApp from './components/MainApp';
import KioskChat from './components/KioskChat';
import LandingPage from './components/pages/LandingPage';
import LoginPage from './components/pages/LoginPage';
import CartPage from './components/pages/CartPage';
import CheckoutPage from './components/pages/CheckoutPage';
import ProductCatalog from './components/pages/ProductCatalog';
import ProductDetail from './components/pages/ProductDetail';

function App() {
  return (
    <CartProvider>
      <Router>
        <div className="min-h-screen bg-background">
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/chat" element={<MainApp />} />
            <Route path="/kiosk" element={<KioskChat />} />
            <Route path="/products" element={<ProductCatalog />} />
            <Route path="/products/:sku" element={<ProductDetail />} />
            <Route path="/cart" element={<CartPage />} />
            <Route path="/checkout" element={<CheckoutPage />} />
          </Routes>
        </div>
      </Router>
    </CartProvider>
  );
}

export default App;
