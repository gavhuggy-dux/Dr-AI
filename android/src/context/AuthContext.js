import React, { createContext, useState, useContext, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import apiClient from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [user, setUser] = useState(null);

  useEffect(() => {
    checkAuth();
  }, []);

  async function checkAuth() {
    try {
      const token = await AsyncStorage.getItem('auth_token');
      if (token) {
        apiClient.token = token;
        setIsLoggedIn(true);
        try {
          const profile = await apiClient.getProfile();
          setUser(profile);
        } catch (e) {
          // If token is expired, clear it
          await logout();
        }
      }
    } catch (e) {
      console.error('Auth check failed:', e);
    } finally {
      setIsLoading(false);
    }
  }

  async function login(email, password) {
    const result = await apiClient.login(email, password);
    setIsLoggedIn(true);
    try {
      const profile = await apiClient.getProfile();
      setUser(profile);
    } catch (e) {
      console.error('Failed to fetch profile after login:', e);
    }
    return result;
  }

  async function logout() {
    await apiClient.clearToken();
    await AsyncStorage.removeItem('patient_id');
    setIsLoggedIn(false);
    setUser(null);
  }

  async function refreshUser() {
    try {
      const profile = await apiClient.getProfile();
      setUser(profile);
    } catch (e) {
      console.error('Failed to refresh user:', e);
    }
  }

  return (
    <AuthContext.Provider value={{ isLoggedIn, isLoading, user, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
