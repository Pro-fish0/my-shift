import { useState, useEffect } from 'react';
import { getShiftCapacities, setShiftCapacity, exportSchedule, syncUsers } from '../services/api';

const AdminDashboard = () => {
  const [capacities, setCapacities] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [unsavedChanges, setUnsavedChanges] = useState({});
  const [isSaving, setIsSaving] = useState(false);
  const [selectedDate, setSelectedDate] = useState({
    month: new Date().getMonth() + 2 > 12 ? 1 : new Date().getMonth() + 2,
    year: new Date().getMonth() + 2 > 12 ? new Date().getFullYear() + 1 : new Date().getFullYear()
  });

  const shifts = [
    { name: 'Morning', color: 'bg-blue-100' },
    { name: 'Evening', color: 'bg-orange-100' },
    { name: 'Night', color: 'bg-purple-100' }
  ];

  const months = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];

  const years = Array.from({ length: 10 }, (_, i) => new Date().getFullYear() + i);
  const daysInMonth = new Date(selectedDate.year, selectedDate.month, 0).getDate();

  useEffect(() => {
    fetchCapacities();
  }, [selectedDate]);

  const handleDateChange = (type, value) => {
    setSelectedDate(prev => ({
      ...prev,
      [type]: parseInt(value)
    }));
    setUnsavedChanges({});
  };

  // Get the total capacity (including any unsaved changes)
  const getTotalCapacity = (day, shiftType) => {
    const key = `${day}_${shiftType}`;
    if (unsavedChanges[key]) {
      return unsavedChanges[key].value;
    }
    return capacities[key]?.total || 0;
  };

  // Get the number of taken slots
  const getTakenSlots = (day, shiftType) => {
    const key = `${day}_${shiftType}`;
    const capacity = capacities[key];
    return capacity ? (capacity.total - capacity.available) : 0;
  };

  const handleCapacityChange = (day, shiftType, value) => {
    const numericValue = value === '' ? 0 : Math.max(0, parseInt(value) || 0);
    const takenSlots = getTakenSlots(day, shiftType);
    
    // Prevent setting capacity below number of taken slots
    if (numericValue < takenSlots) {
      alert(`Cannot set capacity below ${takenSlots} (number of slots already taken)`);
      return;
    }

    const key = `${day}_${shiftType}`;
    setUnsavedChanges(prev => ({
      ...prev,
      [key]: {
        day,
        shiftType,
        value: numericValue
      }
    }));
  };

  const handleSubmit = async () => {
    setIsSaving(true);
    try {
      const promises = Object.values(unsavedChanges).map(change => {
        const date = `${selectedDate.year}-${String(selectedDate.month).padStart(2, '0')}-${String(change.day).padStart(2, '0')}`;
        return setShiftCapacity(date, change.shiftType, change.value);
      });

      await Promise.all(promises);
      await fetchCapacities();
      setUnsavedChanges({});
      alert('Capacities updated successfully!');
    } catch (err) {
      console.error('Error details:', err);
      alert('Failed to update capacities: ' + (err.message || 'Unknown error'));
    } finally {
      setIsSaving(false);
    }
  };

  const fetchCapacities = async () => {
    try {
      const date = `${selectedDate.year}-${String(selectedDate.month).padStart(2, '0')}-01`;
      const data = await getShiftCapacities(date);
      setCapacities(data);
    } catch (err) {
      setError('Failed to load shift capacities');
    } finally {
      setIsLoading(false);
    }
  };

  const handleExport = async () => {
    try {
      const blob = await exportSchedule(selectedDate.month, selectedDate.year);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `schedule_${selectedDate.year}_${selectedDate.month}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Export error:', error);
      alert('Failed to export schedule');
    }
  };

  const handleSyncUsers = async () => {
    try {
      await syncUsers();
      alert('Users synchronized successfully');
    } catch (error) {
      alert('Failed to sync users: ' + error.message);
    }
  };

  if (isLoading) return <div className="text-center p-4">Loading...</div>;
  if (error) return <div className="text-center p-4 text-red-600">{error}</div>;

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="mb-6 bg-white rounded-lg shadow-md p-4">
        <div className="flex justify-between items-center mb-4">
          <h1 className="text-2xl font-bold">Shift Capacity Management</h1>
          
          <div className="flex gap-4 items-center">
            <div className="flex gap-2">
              <select
                value={selectedDate.month}
                onChange={(e) => handleDateChange('month', e.target.value)}
                className="px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {months.map((month, index) => (
                  <option key={month} value={index + 1}>{month}</option>
                ))}
              </select>

              <select
                value={selectedDate.year}
                onChange={(e) => handleDateChange('year', e.target.value)}
                className="px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {years.map(year => (
                  <option key={year} value={year}>{year}</option>
                ))}
              </select>
            </div>

            <button
              onClick={() => setUnsavedChanges({})}
              disabled={isSaving || Object.keys(unsavedChanges).length === 0}
              className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 
                       transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              Reset Changes
            </button>
            <button
              onClick={handleSubmit}
              disabled={isSaving || Object.keys(unsavedChanges).length === 0}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 
                       transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              {isSaving ? 'Saving...' : 'Save All Changes'}
            </button>
            <button
              onClick={handleExport}
              className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors"
            >
              Export Schedule (CSV)
            </button>
            <button
              onClick={handleSyncUsers}
              className="px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition-colors"
            >
              Sync Users
            </button>
          </div>
        </div>

        <div className="grid grid-cols-7 gap-2">
          {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
            <div key={day} className="text-center font-semibold py-2">{day}</div>
          ))}
          
          {[...Array(new Date(selectedDate.year, selectedDate.month - 1, 1).getDay())].map((_, i) => (
            <div key={`empty-${i}`} className="aspect-square"></div>
          ))}

          {[...Array(daysInMonth)].map((_, index) => {
            const day = index + 1;
            return (
              <div key={day} className="border rounded-lg overflow-hidden">
                <div className="text-xs font-semibold p-1 bg-gray-50 border-b">
                  {day}
                </div>
                <div className="flex flex-col h-24">
                  {shifts.map(shift => {
                    const key = `${day}_${shift.name}`;
                    const hasChanges = unsavedChanges[key];
                    const totalCapacity = getTotalCapacity(day, shift.name);
                    const takenSlots = getTakenSlots(day, shift.name);
                    const availableSlots = totalCapacity - takenSlots;
                    
                    return (
                      <div
                        key={`${day}-${shift.name}`}
                        className={`
                          flex-1 relative ${shift.color}
                          ${hasChanges ? 'ring-2 ring-blue-400 ring-inset' : ''}
                        `}
                      >
                        <input
                          type="number"
                          min={takenSlots}
                          value={totalCapacity}
                          onChange={(e) => handleCapacityChange(day, shift.name, e.target.value)}
                          className="absolute inset-0 w-full h-full bg-transparent 
                                   text-center focus:outline-none focus:ring-2 
                                   focus:ring-blue-500 ring-inset"
                        />
                        <div className="absolute top-0 right-1 text-xs text-gray-500">
                          Used: {takenSlots}
                        </div>
                        <div className="absolute bottom-0 right-1 text-xs text-gray-500">
                          Free: {availableSlots}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;