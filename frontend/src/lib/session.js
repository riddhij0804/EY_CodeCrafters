// Lightweight session persistence utilities shared by Chat and Kiosk
const SESSION_TOKEN_KEY = 'ey_session_token';
const SESSION_PHONE_KEY = 'ey_session_phone';
const SESSION_ADDRESS_KEY = 'ey_checkout_address';

export function getSessionToken() {
  try { return localStorage.getItem(SESSION_TOKEN_KEY); } catch { return null; }
}

export function setSessionToken(token) {
  try { localStorage.setItem(SESSION_TOKEN_KEY, token); } catch {}
}

export function clearSessionToken() {
  try { localStorage.removeItem(SESSION_TOKEN_KEY); } catch {}
}

export function getPhone() {
  try { return localStorage.getItem(SESSION_PHONE_KEY); } catch { return null; }
}

export function setPhone(phone) {
  try { localStorage.setItem(SESSION_PHONE_KEY, phone); } catch {}
}

export function clearPhone() {
  try { localStorage.removeItem(SESSION_PHONE_KEY); } catch {}
}

export function clearAll() {
  clearSessionToken();
  clearPhone();
  clearAddress();
}

export function getAddress() {
  try {
    const raw = localStorage.getItem(SESSION_ADDRESS_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function setAddress(address) {
  try {
    if (!address) {
      localStorage.removeItem(SESSION_ADDRESS_KEY);
      return;
    }
    localStorage.setItem(SESSION_ADDRESS_KEY, JSON.stringify(address));
  } catch {}
}

export function clearAddress() {
  try { localStorage.removeItem(SESSION_ADDRESS_KEY); } catch {}
}

export default {
  getSessionToken,
  setSessionToken,
  clearSessionToken,
  getPhone,
  setPhone,
  clearPhone,
  getAddress,
  setAddress,
  clearAddress,
  clearAll,
};
