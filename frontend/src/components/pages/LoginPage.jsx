import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import authService from '../../services/authService';
import sessionStore from '../../lib/session';

const initialForm = {
  name: '',
  age: '',
  gender: '',
  phone_number: '',
  city: '',
};

const genderOptions = ['Female', 'Male', 'Non-binary', 'Prefer not to say'];

const LoginPage = () => {
  const [form, setForm] = useState(initialForm);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const navigate = useNavigate();

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

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!form.name.trim() || !form.phone_number.trim()) {
      setError('Name and phone number are required.');
      return;
    }

    setIsSubmitting(true);
    setError('');

    try {
      const payload = {
        name: form.name.trim(),
        age: form.age ? Number(form.age) : undefined,
        gender: form.gender || undefined,
        phone_number: form.phone_number.trim(),
        city: form.city.trim() || undefined,
      };

      const response = await authService.loginCustomer(payload);

      sessionStore.clearAll();
      sessionStore.setSessionToken(response.session_token);
      sessionStore.setPhone(response.session?.phone || payload.phone_number);
      sessionStore.setProfile(response.customer || response.session?.customer_profile || {});

      const assignedId = response.customer?.customer_id || response.customer?.customerId;
      setSuccess(assignedId ? `Session ready! Your customer ID is ${assignedId}. Redirecting you now...` : 'Login successful. Redirecting you now...');
      setTimeout(() => navigate('/'), 1200);
    } catch (submitError) {
      setError(submitError?.message || 'Failed to create session.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-orange-50 via-yellow-50 to-red-50 px-4">
      <div className="w-full max-w-xl bg-white/95 backdrop-blur shadow-xl rounded-2xl border border-red-100 p-8">
        <h1 className="text-3xl font-semibold text-red-700 text-center mb-6">Customer Login</h1>
        <p className="text-sm text-gray-600 text-center mb-10">
          Sign in once and reuse your session on WhatsApp, Kiosk, and other channels without re-entering your phone number. We will create your customer ID automatically when you log in.
        </p>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <label className="flex flex-col gap-2 text-sm font-medium text-gray-700">
              Name
              <input
                name="name"
                value={form.name}
                onChange={handleChange}
                placeholder="Full name"
                className="border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-red-400"
              />
            </label>
            <label className="flex flex-col gap-2 text-sm font-medium text-gray-700">
              Phone Number
              <input
                name="phone_number"
                value={form.phone_number}
                onChange={handleChange}
                placeholder="Digits only"
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
          </div>
          {error && <p className="text-sm text-red-600 text-center">{error}</p>}
          {success && <p className="text-sm text-green-600 text-center">{success}</p>}
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full bg-gradient-to-r from-red-600 to-orange-500 text-white py-3 rounded-lg font-semibold tracking-wide shadow-lg hover:from-red-500 hover:to-orange-400 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {isSubmitting ? 'Creating session...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default LoginPage;
