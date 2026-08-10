import axios from 'axios';

// API Configuration
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Request interceptor for adding auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('zima_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // Handle unauthorized access
      localStorage.removeItem('zima_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authApi = {
  login: async (username, password) => {
    try {
      const response = await api.post('/token', {
        username,
        password
      }, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      });
      return response.data;
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  },

  getCurrentUser: async () => {
    try {
      const response = await api.get('/profiles/me');
      return response.data;
    } catch (error) {
      console.error('Failed to get current user:', error);
      throw error;
    }
  }
};

export const profileApi = {
  getAllProfiles: async (limit = 10, offset = 0) => {
    try {
      const response = await api.get('/profiles', {
        params: { limit, offset }
      });
      return response.data;
    } catch (error) {
      console.error('Failed to fetch profiles:', error);
      throw error;
    }
  },

  getProfileById: async (profileId) => {
    try {
      const response = await api.get(`/profiles/${profileId}`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch profile:', error);
      throw error;
    }
  },

  searchProfiles: async (query, limit = 10) => {
    try {
      const response = await api.get('/profiles', {
        params: { q: query, limit }
      });
      return response.data;
    } catch (error) {
      console.error('Search failed:', error);
      throw error;
    }
  },

  createProfile: async (profileData) => {
    try {
      const response = await api.post('/profiles', profileData);
      return response.data;
    } catch (error) {
      console.error('Failed to create profile:', error);
      throw error;
    }
  },

  updateProfile: async (profileId, updates) => {
    try {
      const response = await api.put(`/profiles/${profileId}`, updates);
      return response.data;
    } catch (error) {
      console.error('Failed to update profile:', error);
      throw error;
    }
  }
};

export const matchApi = {
  findMatches: async (userId, limit = 5) => {
    try {
      const response = await api.get(`/match/${userId}`, {
        params: { limit }
      });
      return response.data;
    } catch (error) {
      console.error('Failed to find matches:', error);
      throw error;
    }
  },

  requestConnection: async (toUserId, message) => {
    try {
      const response = await api.post('/match/request', {
        to_user_id: toUserId,
        message
      });
      return response.data;
    } catch (error) {
      console.error('Failed to send connection request:', error);
      throw error;
    }
  },

  getConnectionRequests: async (userId) => {
    try {
      const response = await api.get(`/match/${userId}/requests`);
      return response.data;
    } catch (error) {
      console.error('Failed to get connection requests:', error);
      throw error;
    }
  }
};

export const neurotypeApi = {
  getAllNeurotypes: async () => {
    try {
      const response = await api.get('/neurotypes');
      return response.data;
    } catch (error) {
      console.error('Failed to fetch neurotypes:', error);
      throw error;
    }
  }
};

export default api;
