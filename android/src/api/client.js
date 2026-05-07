import AsyncStorage from '@react-native-async-storage/async-storage';

const BASE_URL = 'http://100.82.200.47:5003';

class ApiClient {
  constructor() {
    this.token = null;
  }

  async getToken() {
    if (!this.token) {
      this.token = await AsyncStorage.getItem('auth_token');
    }
    return this.token;
  }

  async setToken(token) {
    this.token = token;
    await AsyncStorage.setItem('auth_token', token);
  }

  async clearToken() {
    this.token = null;
    await AsyncStorage.removeItem('auth_token');
  }

  async getPatientId() {
    const pid = await AsyncStorage.getItem('patient_id');
    return pid;
  }

  async setPatientId(id) {
    await AsyncStorage.setItem('patient_id', String(id));
  }

  async request(endpoint, options = {}) {
    const token = await this.getToken();
    const headers = {
      ...(options.headers || {}),
    };

    // If not form data, set content-type
    if (!(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const url = `${BASE_URL}${endpoint}`;
    
    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      const contentType = response.headers.get('content-type');
      let data;
      if (contentType && contentType.includes('application/json')) {
        data = await response.json();
      } else {
        data = await response.text();
      }

      if (!response.ok) {
        const errorMsg = typeof data === 'object' && data.error ? data.error : 
                        typeof data === 'object' && data.message ? data.message : 
                        `Request failed with status ${response.status}`;
        throw new Error(errorMsg);
      }

      return data;
    } catch (error) {
      if (error.message.includes('Network request failed')) {
        throw new Error('Unable to connect to server. Please check your connection.');
      }
      throw error;
    }
  }

  // Auth
  async register(data) {
    const formData = new FormData();
    formData.append('first_name', data.first_name);
    formData.append('last_name', data.last_name);
    formData.append('email', data.email);
    formData.append('password', data.password);
    formData.append('date_of_birth', data.date_of_birth);
    formData.append('phone', data.phone);
    return this.request('/register', {
      method: 'POST',
      body: formData,
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  }

  async login(email, password) {
    const data = await this.request('/api/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    if (data.token) {
      await this.setToken(data.token);
    }
    if (data.patient_id) {
      await this.setPatientId(data.patient_id);
    }
    return data;
  }

  // Profile
  async getProfile() {
    return this.request('/api/patient/profile');
  }

  async updateProfile(data) {
    return this.request('/api/patient/profile', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async getOnboardingProgress() {
    return this.request('/api/patient/onboarding-progress');
  }

  // Credits
  async getCreditBalance() {
    return this.request('/api/credits/balance');
  }

  async getCreditPackages() {
    return this.request('/api/credits/packages');
  }

  async createCheckoutSession(packageId) {
    return this.request('/api/credits/create-checkout-session', {
      method: 'POST',
      body: JSON.stringify({ package_id: packageId }),
    });
  }

  async getCreditHistory() {
    return this.request('/api/credits/history');
  }

  // Appointments
  async getAppointments() {
    return this.request('/api/appointments');
  }

  async bookAppointment(data) {
    return this.request('/api/appointments/book', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async startAppointment(id) {
    return this.request(`/api/appointments/start/${id}`, {
      method: 'POST',
    });
  }

  async completeAppointment(id) {
    return this.request(`/api/appointments/complete/${id}`, {
      method: 'POST',
    });
  }

  // Ads
  async getNextAd() {
    return this.request('/api/ads/next');
  }

  async getAdTickers() {
    return this.request('/api/ads/tickers');
  }

  async clickAd(id) {
    return this.request(`/api/ads/click/${id}`, {
      method: 'POST',
    });
  }
}

const apiClient = new ApiClient();
export default apiClient;
