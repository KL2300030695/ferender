import React, { createContext, useState, useEffect, useContext } from 'react';
import axios from 'axios';

const AuthContext = createContext();
const API_BASE_URL = 'http://localhost:8000';

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('wellness_token') || null);
  const [isLoading, setIsLoading] = useState(true);

  // Set default auth header if token exists
  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      localStorage.setItem('wellness_token', token);
      fetchUserProfile();
    } else {
      delete axios.defaults.headers.common['Authorization'];
      localStorage.removeItem('wellness_token');
      setIsLoading(false);
    }
  }, [token]);

  const fetchUserProfile = async () => {
    try {
        const response = await axios.get(`${API_BASE_URL}/users/me`);
        setUser(response.data);
    } catch (error) {
        console.error("Token expired or invalid");
        logout();
    } finally {
        setIsLoading(false);
    }
  }

  const login = async (email, password) => {
    const response = await axios.post(`${API_BASE_URL}/auth/login`, { email, password });
    setToken(response.data.access_token);
    return response.data;
  };

  const register = async (firstName, email, password) => {
    const response = await axios.post(`${API_BASE_URL}/auth/register`, { 
        first_name: firstName, 
        email, 
        password 
    });
    setToken(response.data.access_token);
    return response.data;
  };

  const logout = () => {
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, register, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
