import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import authService from '../../services/authService';
import sessionStore from '../../lib/session';
import Navbar from '@/components/Navbar.jsx';

const initialForm = {
  name: '',
  age: '',
  gender: '',
  phone_number: '',
  password: '',
  confirmPassword: '',
  city: '',
  building_name: '',
  address_landmark: '',
};

const genderOptions = ['Female', 'Male', 'Non-binary', 'Prefer not to say'];

const LoginPage = () => {
  const [form, setForm] = useState(initialForm);
  const [mode, setMode] = useState('login'); // 'login' or 'signup'
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const navigate = useNavigate();
  const location = useLocation();
  const redirectTo = location.state?.redirectTo || '/';

  const handleChange = (event) => {
    const { name, value } = event.target;
    let nextValue = value;

    if (name === 'phone_number') {
      nextValue = value.replace(/[^0-9]/g, '');
    }

    if (name === 'age') {
      nextValue = value.replace(/[^0-9]/g, '');
    }

    setForm((prev) => ({ ...prev, [name]: nextValue }));
    setError('');
    setSuccess('');
  };

  const toggleMode = () => {
    setMode((prev) => (prev === 'login' ? 'signup' : 'login'));
    setError('');
    setSuccess('');
    setForm(initialForm);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    
    // Validate required fields based on mode
    if (!form.phone_number.trim()) {
      setError('Phone number is required.');
      return;
    }
    
    if (!form.password.trim()) {
      setError('Password is required.');
      return;
    }

    if (form.password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }

    if (mode === 'signup') {
      // Additional validation for signup
      if (!form.name.trim()) {
        setError('Name is required for signup.');
        return;
      }
      
      if (form.password !== form.confirmPassword) {
        setError('Passwords do not match.');
        return;
      }
    }

    setIsSubmitting(true);
    setError('');

    try {
      let response;
      
      if (mode === 'signup') {
        // Signup flow
        const payload = {
          name: form.name.trim(),
          phone_number: form.phone_number.trim(),
          password: form.password,
          age: form.age ? Number(form.age) : undefined,
          gender: form.gender || undefined,
          city: form.city.trim() || undefined,
          building_name: form.building_name.trim() || undefined,
          address_landmark: form.address_landmark.trim() || undefined,
          channel: 'web',
        };
        
        response = await authService.signup(payload);
        setSuccess('Account created successfully! Redirecting...');
        
      } else {
        // Login flow
        const payload = {
          phone_number: form.phone_number.trim(),
          password: form.password,
          channel: 'web',
        };
        
        response = await authService.login(payload);
        setSuccess('Login successful! Redirecting...');
      }

      // Store session data
      sessionStore.clearAll();
      sessionStore.setSessionToken(response.session_token);
      sessionStore.setPhone(response.session?.phone || form.phone_number);
      sessionStore.setProfile(response.customer || response.session?.customer_profile || {});

      // Redirect after brief delay
      setTimeout(() => navigate(redirectTo, { replace: true }), 1200);
      
    } catch (submitError) {
      const errorMsg = submitError?.message || submitError?.body?.detail || 'Authentication failed.';
      setError(errorMsg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 via-yellow-50 to-red-50">
      <Navbar />
      <div className="pt-20 flex items-center justify-center px-4 pb-10">
        <div className="w-full max-w-2xl bg-white/95 backdrop-blur shadow-xl rounded-2xl border border-red-100 p-8">
          <h1 className="text-3xl font-semibold text-red-700 text-center mb-4">
            {mode === 'login' ? 'Customer Login' : 'Create Account'}
          </h1>
          <p className="text-sm text-gray-600 text-center mb-8">
            {mode === 'login' 
              ? 'Sign in with your phone number and password. Your session works across web, WhatsApp, and kiosk.'
              : 'Create your account with a password. You can use it on web, WhatsApp, and kiosk channels.'
            }
          </p>
          
          <form onSubmit={handleSubmit} className="space-y-6">
            {mode === 'signup' && (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <label className="flex flex-col gap-2 text-sm font-medium text-gray-700 md:col-span-2">
                    Name *
                    <input
                      name="name"
                      value={form.name}
                      onChange={handleChange}
                      placeholder="Full name"
                      required
                      className="border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-red-400"
                    />
                  </label>
                  
                  <label className="flex flex-col gap-2 text-sm font-medium text-gray-700">
                    Age
                    <input
                      name="age"
                      value={form.age}
                      onChange={handleChange}
                      type="number"
                      min="0"
                      placeholder="Optional"
                      className="border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-red-400"
                    />
                  </label>
                  
                  <label className="flex flex-col gap-2 text-sm font-medium text-gray-700">
                    Gender
                    <select
                      name="gender"
                      value={form.gender}
                      onChange={handleChange}
                      className="border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-red-400"
                    >
                      <option value="">Select gender</option>
                      {genderOptions.map((option) => (
                        <option key={option} value={option}>{option}</option>
                      ))}
                    </select>
                  </label>
                  
                  <label className="flex flex-col gap-2 text-sm font-medium text-gray-700 md:col-span-2">
                    City
                    <input
                      name="city"
                      value={form.city}
                      onChange={handleChange}
                      placeholder="City or locality"
                      className="border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-red-400"
                    />
                  </label>
                  
                  <label className="flex flex-col gap-2 text-sm font-medium text-gray-700">
                    Building Name
                    <input
                      name="building_name"
                      value={form.building_name}
                      onChange={handleChange}
                      placeholder="Optional"
                      className="border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-red-400"
                    />
                  </label>
                  
                  <label className="flex flex-col gap-2 text-sm font-medium text-gray-700">
                    Address Landmark
                    <input
                      name="address_landmark"
                      value={form.address_landmark}
                      onChange={handleChange}
                      placeholder="Optional"
                      className="border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-red-400"
                    />
                  </label>
                </div>
              </>
            )}
            
            <div className="grid grid-cols-1 gap-6">
              <label className="flex flex-col gap-2 text-sm font-medium text-gray-700">
                Phone Number *
                <input
                  name="phone_number"
                  value={form.phone_number}
                  onChange={handleChange}
                  placeholder="10-digit phone number"
                  required
                  className="border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-red-400"
                />
              </label>
              
              <label className="flex flex-col gap-2 text-sm font-medium text-gray-700">
                Password *
                <input
                  name="password"
                  type="password"
                  value={form.password}
                  onChange={handleChange}
                  placeholder="Minimum 6 characters"
                  required
                  minLength={6}
                  className="border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-red-400"
                />
              </label>
              
              {mode === 'signup' && (
                <label className="flex flex-col gap-2 text-sm font-medium text-gray-700">
                  Confirm Password *
                  <input
                    name="confirmPassword"
                    type="password"
                    value={form.confirmPassword}
                    onChange={handleChange}
                    placeholder="Re-enter password"
                    required
                    minLength={6}
                    className="border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-red-400"
                  />
                </label>
              )}
            </div>
            
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                {error}
              </div>
            )}
            
            {success && (
              <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg text-sm">
                {success}
              </div>
            )}
            
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full bg-gradient-to-r from-red-600 to-orange-500 text-white py-3 rounded-lg font-semibold tracking-wide shadow-lg hover:from-red-500 hover:to-orange-400 disabled:opacity-60 disabled:cursor-not-allowed transition-all"
            >
              {isSubmitting 
                ? (mode === 'login' ? 'Signing in...' : 'Creating account...') 
                : (mode === 'login' ? 'Sign In' : 'Create Account')
              }
            </button>
          </form>
          
          <div className="mt-6 text-center">
            <button
              onClick={toggleMode}
              className="text-sm text-red-600 hover:text-red-700 font-medium"
            >
              {mode === 'login' 
                ? "Don't have an account? Sign up" 
                : 'Already have an account? Sign in'
              }
            </button>
          </div>
          
          {mode === 'login' && (
            <div className="mt-4 text-center">
              <p className="text-xs text-gray-500">
                WhatsApp users: Continue using your phone number without password
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
