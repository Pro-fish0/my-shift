import { useState, useEffect } from 'react';
import Login from './components/Login';
import ShiftSelector from './components/ShiftSelector';
import AdminDashboard from './components/AdminDashboard';

function App() {
  const [user, setUser] = useState(null);

  // Optional: Persist user session using localStorage
  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    const token = localStorage.getItem('token');
    if (storedUser && token) {
      setUser(JSON.parse(storedUser));
      // Optionally, verify token validity here
    }
  }, []);

  const handleLogin = (userData) => {
    setUser(userData);
    localStorage.setItem('user', JSON.stringify(userData));
    // Optionally, store token if available
    // localStorage.setItem('token', userData.token);
  };

  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  };

  if (!user) {
    return <Login onLogin={handleLogin} />;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            {/* Logo */}
            <div className="flex items-center">
              <img
                src="https://my.srca.org.sa/logo.png"
                alt="SRCA Logo"
                className="h-8 w-auto"
              />
            </div>
            {/* User Info and Logout */}
            <div className="flex items-center gap-4">
              <span className="text-gray-700">Welcome, {user.name}</span>
              <button
                onClick={handleLogout}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {user.role === 'admin' ? (
          <AdminDashboard />
        ) : (
          <ShiftSelector employeeId={user.employeeId} />
        )}
      </main>
    </div>
  );
}

export default App;
