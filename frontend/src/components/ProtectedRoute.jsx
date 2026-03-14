import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Brain } from 'lucide-react';

const ProtectedRoute = () => {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-gray-900 text-white flex-col gap-4">
        <Brain size={48} className="pulse text-purple-500" />
        <div className="text-xl font-display animate-pulse">Loading Identity...</div>
      </div>
    );
  }

  // If no user is logged in, restrict access to these routes
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
};

export default ProtectedRoute;
