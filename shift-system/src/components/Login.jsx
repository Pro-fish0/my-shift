import { useState } from 'react';
import { loginUser } from '../services/api';

const Login = ({ onLogin }) => {
  const [employeeId, setEmployeeId] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const { user } = await loginUser(employeeId, password);
      localStorage.setItem('user', JSON.stringify(user));
      onLogin(user);
    } catch (err) {
      setError('Invalid employee ID or password');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="srca-header">
        <div className="srca-container flex items-center">
          <img src="/images/logo.png" alt="SRCA Logo" className="srca-logo" />
        </div>
      </header>
      
      <div className="srca-container flex items-center justify-center mt-16">
        <div className="srca-card w-full max-w-md">
          <div className="text-center mb-8">
            <img src="/images/logo.png" alt="SRCA Logo" className="h-16 mx-auto mb-4" />
            <h2 className="text-2xl font-bold text-gray-900">
              Shift Management System
            </h2>
            <p className="mt-2 text-gray-600">
              Please sign in with your employee ID
            </p>
          </div>
        
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="bg-red-50 p-4 rounded text-red-600 text-sm">
              {error}
            </div>
          )}
          
          <div className="rounded-md shadow-sm space-y-4">
            <div>
              <label htmlFor="employee-id" className="block text-sm font-medium text-gray-700">
                Employee ID
              </label>
              <input
                id="employee-id"
                name="employeeId"
                type="text"
                required
                value={employeeId}
                onChange={(e) => setEmployeeId(e.target.value)}
                className="mt-1 appearance-none rounded-lg relative block w-full px-3 py-2 border 
                         border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none 
                         focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                placeholder="Enter your employee ID"
              />
            </div>
            
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 appearance-none rounded-lg relative block w-full px-3 py-2 border 
                         border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none 
                         focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                placeholder="Enter your password"
              />
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={isLoading}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent 
                       text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 
                       focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500
                       disabled:bg-blue-300 disabled:cursor-not-allowed"
            >
              {isLoading ? 'Signing in...' : 'Sign in'}
            </button>
          </div>
        </form>
        </div>
      </div>
    </div>
  );
};

export default Login;