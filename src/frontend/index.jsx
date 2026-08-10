import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import App from './App';
import Login from './Login';
import './index.css';

const Main = () => {
  const [user, setUser] = React.useState(null);

  React.useEffect(() => {
    // Check if user is already logged in
    const token = localStorage.getItem('zima_token');
    if (token) {
      // In a real app, you would verify the token and fetch user data
      // For demo purposes, we'll just set a mock user
      setUser({
        id: 'current-user',
        display_name: 'Current User',
        neurotype: 'developer'
      });
    }
  }, []);

  const handleLogin = (userData) => {
    setUser(userData);
  };

  const handleLogout = () => {
    localStorage.removeItem('zima_token');
    setUser(null);
  };

  return (
    <Router>
      <Routes>
        <Route
          path="/login"
          element={<Login onLogin={handleLogin} />}
        />
        <Route
          path="/*"
          element={user ? (
            <App user={user} onLogout={handleLogout} />
          ) : (
            <Login onLogin={handleLogin} />
          )}
        />
      </Routes>
    </Router>
  );
};

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <Main />
  </React.StrictMode>
);
