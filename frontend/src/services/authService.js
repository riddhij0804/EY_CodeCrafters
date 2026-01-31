import API_ENDPOINTS, { apiCall } from '../config/api';

export async function loginCustomer(payload) {
  return apiCall(API_ENDPOINTS.SESSION_LOGIN, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export default {
  loginCustomer,
};
