import React from 'react';
import Login from './components/Login';
import ShiftSelector from './components/ShiftSelector';
import AdminDashboard from './components/AdminDashboard';

function App() {
  const [user, setUser] = React.useState(null);

  React.useEffect(() => {
    const storedUser = localStorage.getItem('user');
    const token = localStorage.getItem('token');
    if (storedUser && token) {
      setUser(JSON.parse(storedUser));
    }
  }, []);

  const handleLogin = (userData) => {
    setUser(userData);
    localStorage.setItem('user', JSON.stringify(userData));
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
      {/* Main Header */}
      <header className="bg-white border-b">
        <div className="max-w-7xl mx-auto">
          {/* Top Header with Logo and User Info */}
          <div className="h-16 flex items-center justify-between px-4 relative">
            {/* Logo Section */}
            <div className="flex items-center space-x-2">
              <div className="flex-shrink-0">
                <img src="/images/logo.png" alt="SRCA Logo" className="h-10 w-auto" />
              </div>
              <div className="hidden md:flex flex-col">
                <span className="text-lg font-semibold text-gray-900">SRCA</span>
                <span className="text-sm text-gray-500">Shift Management</span>
              </div>
            </div>

            {/* Centered User Info */}
            <div className="absolute left-1/2 top-1/2 transform -translate-x-1/2 -translate-y-1/2
                          flex items-center space-x-3 bg-gray-50 px-4 py-2 rounded-full">
              <span className="text-sm font-medium text-gray-700">{user.name}</span>
              <span className="h-4 w-px bg-gray-300"></span>
              <span className="text-sm text-gray-500">{user.role}</span>
            </div>

            {/* Logout Button */}
            <button
              onClick={handleLogout}
              className="px-4 py-2 bg-red-50 text-red-700 rounded-lg hover:bg-red-100 
                       transition-colors duration-200 border border-red-200 font-medium"
            >
              Logout
            </button>
          </div>

          {/* Bottom Header with Current Section */}
          <div className="h-12 border-t flex items-center px-4 bg-gray-50">
            <span className="font-medium text-gray-600">
              {user.role === 'admin' ? 'Administration Dashboard' : 'Employee Portal'}
            </span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
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