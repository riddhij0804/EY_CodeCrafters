import API_ENDPOINTS, { apiCall } from '../config/api';

// ===========================
// Existing Login (Password-less - WhatsApp flow)
// ===========================

export async function loginCustomer(payload) {
  return apiCall(API_ENDPOINTS.SESSION_LOGIN, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

// ===========================
// New Password-Based Authentication
// ===========================

/**
 * Signup with password (website channel)
 */
export async function signup(payload) {
  return apiCall(API_ENDPOINTS.AUTH_SIGNUP, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * Login with phone + password (website channel)
 */
export async function login(payload) {
  return apiCall(API_ENDPOINTS.AUTH_LOGIN, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * Logout current session
 * Requires X-Session-Token header
 */
export async function logout(sessionToken) {
  return apiCall(API_ENDPOINTS.AUTH_LOGOUT, {
    method: 'POST',
    headers: {
      'X-Session-Token': sessionToken,
    },
  });
}

/**
 * Generate QR token for kiosk authentication
 * Requires user to be logged in with session token
 */
export async function initQRAuth(phoneNumber, sessionToken) {
  return apiCall(API_ENDPOINTS.AUTH_QR_INIT, {
    method: 'POST',
    headers: {
      'X-Session-Token': sessionToken,
    },
    body: JSON.stringify({
      phone_number: phoneNumber,
    }),
  });
}

/**
 * Verify QR token and create kiosk session
 * Used by kiosk after scanning QR code
 */
export async function verifyQRAuth(qrToken, channel = 'kiosk') {
  return apiCall(API_ENDPOINTS.AUTH_QR_VERIFY, {
    method: 'POST',
    body: JSON.stringify({
      qr_token: qrToken,
      channel: channel,
    }),
  });
}

export default {
  // Legacy (WhatsApp flow - no password)
  loginCustomer,
  
  // New password-based auth
  signup,
  login,
  logout,
  
  // QR auth for kiosk
  initQRAuth,
  verifyQRAuth,
};
