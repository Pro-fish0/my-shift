import { useState } from 'react';
import Login from './components/Login';
import ShiftSelector from './components/ShiftSelector';
import AdminDashboard from './components/AdminDashboard';

function App() {
  const [user, setUser] = useState(null);

  const handleLogin = (userData) => {
    setUser(userData);
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
    <div>
      <nav className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <span className="text-lg font-semibold">
                Welcome, {user.name}
              </span>
            </div>
            <div className="flex items-center">
              <button
                onClick={handleLogout}
                className="ml-4 px-4 py-2 border border-transparent text-sm font-medium rounded-md 
                         text-white bg-gray-600 hover:bg-gray-700"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>

      <main>
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