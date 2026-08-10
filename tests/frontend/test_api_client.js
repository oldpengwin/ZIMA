/**
 * Test API client for ZIMA frontend
 */

const { describe, it, expect, beforeEach, afterEach, vi } = require('vitest');
const axios = require('axios');

// Mock axios
vi.mock('axios');

// Import the API modules
const api = require('../../src/frontend/api.js');

// Mock localStorage
global.localStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn()
};

describe('API Client', () => {
  beforeEach(() => {
    // Reset all mocks before each test
    vi.resetAllMocks();
  });

  describe('authApi', () => {
    describe('login', () => {
      it('should successfully login and return token', async () => {
        const mockResponse = {
          data: {
            access_token: 'test-token',
            token_type: 'bearer'
          }
        };

        axios.post.mockResolvedValue(mockResponse);

        const result = await api.authApi.login('testuser', 'testpass');

        expect(axios.post).toHaveBeenCalledWith('/token', {
          username: 'testuser',
          password: 'testpass'
        }, {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
          }
        });

        expect(result).toEqual({
          access_token: 'test-token',
          token_type: 'bearer'
        });
      });

      it('should handle login error', async () => {
        const mockError = new Error('Login failed');
        axios.post.mockRejectedValue(mockError);

        await expect(api.authApi.login('testuser', 'wrongpass')).rejects.toThrow();
      });
    });

    describe('getCurrentUser', () => {
      it('should get current user with auth token', async () => {
        const mockResponse = {
          data: {
            id: 'user-id',
            display_name: 'Test User',
            neurotype: 'developer'
          }
        };

        axios.get.mockResolvedValue(mockResponse);
        localStorage.getItem.mockReturnValue('test-token');

        const result = await api.authApi.getCurrentUser();

        expect(axios.get).toHaveBeenCalledWith('/profiles/me');
        expect(result).toEqual({
          id: 'user-id',
          display_name: 'Test User',
          neurotype: 'developer'
        });
      });

      it('should handle 401 error and redirect', async () => {
        const mockError = {
          response: {
            status: 401
          }
        };

        axios.get.mockRejectedValue(mockError);
        localStorage.getItem.mockReturnValue('expired-token');

        // Mock window.location
        delete global.window.location;
        global.window = {
          location: {
            href: ''
          }
        };

        await expect(api.authApi.getCurrentUser()).rejects.toThrow();
        expect(localStorage.removeItem).toHaveBeenCalledWith('zima_token');
      });
    });
  });

  describe('profileApi', () => {
    describe('getAllProfiles', () => {
      it('should get all profiles', async () => {
        const mockResponse = {
          data: [
            { id: '1', display_name: 'User 1' },
            { id: '2', display_name: 'User 2' }
          ]
        };

        axios.get.mockResolvedValue(mockResponse);

        const result = await api.profileApi.getAllProfiles(10, 0);

        expect(axios.get).toHaveBeenCalledWith('/profiles', {
          params: { limit: 10, offset: 0 }
        });
        expect(result).toEqual([
          { id: '1', display_name: 'User 1' },
          { id: '2', display_name: 'User 2' }
        ]);
      });
    });

    describe('getProfileById', () => {
      it('should get profile by ID', async () => {
        const mockResponse = {
          data: { id: '1', display_name: 'Test User' }
        };

        axios.get.mockResolvedValue(mockResponse);

        const result = await api.profileApi.getProfileById('1');

        expect(axios.get).toHaveBeenCalledWith('/profiles/1');
        expect(result).toEqual({ id: '1', display_name: 'Test User' });
      });
    });

    describe('searchProfiles', () => {
      it('should search profiles', async () => {
        const mockResponse = {
          data: [{ id: '1', display_name: 'Test User' }]
        };

        axios.get.mockResolvedValue(mockResponse);

        const result = await api.profileApi.searchProfiles('test', 10);

        expect(axios.get).toHaveBeenCalledWith('/profiles', {
          params: { q: 'test', limit: 10 }
        });
        expect(result).toEqual([{ id: '1', display_name: 'Test User' }]);
      });
    });

    describe('createProfile', () => {
      it('should create a profile', async () => {
        const mockResponse = {
          data: { id: 'new-id', display_name: 'New User' }
        };

        axios.post.mockResolvedValue(mockResponse);

        const result = await api.profileApi.createProfile({
          display_name: 'New User',
          neurotype: 'developer'
        });

        expect(axios.post).toHaveBeenCalledWith('/profiles', {
          display_name: 'New User',
          neurotype: 'developer'
        });
        expect(result).toEqual({ id: 'new-id', display_name: 'New User' });
      });
    });

    describe('updateProfile', () => {
      it('should update a profile', async () => {
        const mockResponse = {
          data: { id: '1', display_name: 'Updated User' }
        };

        axios.put.mockResolvedValue(mockResponse);

        const result = await api.profileApi.updateProfile('1', {
          display_name: 'Updated User'
        });

        expect(axios.put).toHaveBeenCalledWith('/profiles/1', {
          display_name: 'Updated User'
        });
        expect(result).toEqual({ id: '1', display_name: 'Updated User' });
      });
    });
  });

  describe('matchApi', () => {
    describe('findMatches', () => {
      it('should find matches for a user', async () => {
        const mockResponse = {
          data: {
            user_id: '1',
            matches: [
              {
                profile: { id: '2', display_name: 'Match 1' },
                score: 0.95
              }
            ]
          }
        };

        axios.get.mockResolvedValue(mockResponse);

        const result = await api.matchApi.findMatches('1', 5);

        expect(axios.get).toHaveBeenCalledWith('/match/1', {
          params: { limit: 5 }
        });
        expect(result).toEqual({
          user_id: '1',
          matches: [
            {
              profile: { id: '2', display_name: 'Match 1' },
              score: 0.95
            }
          ]
        });
      });
    });

    describe('requestConnection', () => {
      it('should send a connection request', async () => {
        const mockResponse = {
          data: {
            id: 'req-1',
            from_user_id: '1',
            to_user_id: '2',
            status: 'pending'
          }
        };

        axios.post.mockResolvedValue(mockResponse);

        const result = await api.matchApi.requestConnection('2', 'Hello!');

        expect(axios.post).toHaveBeenCalledWith('/match/request', {
          to_user_id: '2',
          message: 'Hello!'
        });
        expect(result).toEqual({
          id: 'req-1',
          from_user_id: '1',
          to_user_id: '2',
          status: 'pending'
        });
      });
    });

    describe('getConnectionRequests', () => {
      it('should get connection requests', async () => {
        const mockResponse = {
          data: {
            user_id: '1',
            requests: [
              { id: 'req-1', from_user_id: '2', status: 'pending' }
            ]
          }
        };

        axios.get.mockResolvedValue(mockResponse);

        const result = await api.matchApi.getConnectionRequests('1');

        expect(axios.get).toHaveBeenCalledWith('/match/1/requests');
        expect(result).toEqual({
          user_id: '1',
          requests: [
            { id: 'req-1', from_user_id: '2', status: 'pending' }
          ]
        });
      });
    });
  });

  describe('neurotypeApi', () => {
    describe('getAllNeurotypes', () => {
      it('should get all neurotypes', async () => {
        const mockResponse = {
          data: {
            neurotypes: {
              seedcaster: { id: 'seedcaster', name: 'Seedcaster' },
              fabricant: { id: 'fabricant', name: 'Fabricant' }
            }
          }
        };

        axios.get.mockResolvedValue(mockResponse);

        const result = await api.neurotypeApi.getAllNeurotypes();

        expect(axios.get).toHaveBeenCalledWith('/neurotypes');
        expect(result).toEqual({
          neurotypes: {
            seedcaster: { id: 'seedcaster', name: 'Seedcaster' },
            fabricant: { id: 'fabricant', name: 'Fabricant' }
          }
        });
      });
    });
  });

  describe('Request Interceptor', () => {
    it('should add auth token to requests when available', async () => {
      localStorage.getItem.mockReturnValue('test-token');

      const mockConfig = {
        headers: {}
      };

      // Get the request interceptor
      const requestInterceptor = api.default.interceptors.request.handlers[0];
      const result = await requestInterceptor.fulfilled(mockConfig);

      expect(result.headers.Authorization).toBe('Bearer test-token');
    });

    it('should not add auth token when not available', async () => {
      localStorage.getItem.mockReturnValue(null);

      const mockConfig = {
        headers: {}
      };

      // Get the request interceptor
      const requestInterceptor = api.default.interceptors.request.handlers[0];
      const result = await requestInterceptor.fulfilled(mockConfig);

      expect(result.headers.Authorization).toBeUndefined();
    });
  });

  describe('Response Interceptor', () => {
    it('should pass through successful responses', async () => {
      const mockResponse = { data: { test: 'data' } };

      // Get the response interceptor
      const responseInterceptor = api.default.interceptors.response.handlers[0];
      const result = await responseInterceptor.fulfilled(mockResponse);

      expect(result).toEqual(mockResponse);
    });

    it('should handle 401 error and redirect', async () => {
      const mockError = {
        response: {
          status: 401
        }
      };

      // Mock window.location
      delete global.window.location;
      global.window = {
        location: {
          href: ''
        }
      };

      // Get the response interceptor
      const responseInterceptor = api.default.interceptors.response.handlers[0];

      try {
        await responseInterceptor.rejected(mockError);
      } catch (error) {
        // Should throw the error
        expect(error).toEqual(mockError);
      }

      expect(localStorage.removeItem).toHaveBeenCalledWith('zima_token');
    });
  });
});
