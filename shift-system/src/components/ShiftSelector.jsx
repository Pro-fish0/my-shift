import { useState, useEffect } from 'react';
import { Calendar, Clock, CheckCircle, AlertCircle } from 'lucide-react';
import { getShiftCapacities, submitShiftSelections, getEmployeeShifts } from '../services/api';

const ShiftSelector = ({ employeeId }) => {
  // State declarations
  const [selectedShifts, setSelectedShifts] = useState([]);
  const [capacities, setCapacities] = useState({});
  const [employeeShifts, setEmployeeShifts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [hasSchedule, setHasSchedule] = useState(false);

  // Constants
  const shifts = [
    { name: 'Morning', color: 'bg-blue-100' },
    { name: 'Evening', color: 'bg-orange-100' },
    { name: 'Night', color: 'bg-purple-100' }
  ];

  // Date calculations
  const getNextMonth = () => {
    const today = new Date();
    if (today.getMonth() === 11) {
      return { month: 1, year: today.getFullYear() + 1 };
    }
    return {
      month: today.getMonth() + 2,
      year: today.getFullYear()
    };
  };

  const { month, year } = getNextMonth();
  const daysInMonth = new Date(year, month, 0).getDate();
  const firstDayOfMonth = new Date(year, month - 1, 1).getDay();

  // Helper functions
  const getMonthName = (monthNumber) => {
    return new Date(2024, monthNumber - 1, 1).toLocaleString('default', { month: 'long' });
  };

  const getShiftTypeCount = (shiftType) => 
    selectedShifts.filter(s => s.shift_type === shiftType).length;

  const hasAvailability = (day, shiftType) => {
    const key = `${day}_${shiftType}`;
    const capacity = capacities[key];
    return capacity?.total > 0 && capacity?.available > 0;
  };

  const getConsecutiveDays = (shifts) => {
    const sortedDays = shifts.map(s => s.day).sort((a, b) => a - b);
    let maxConsecutive = 1;
    let currentConsecutive = 1;

    for (let i = 1; i < sortedDays.length; i++) {
      if (sortedDays[i] === sortedDays[i - 1] + 1) {
        currentConsecutive++;
        maxConsecutive = Math.max(maxConsecutive, currentConsecutive);
      } else {
        currentConsecutive = 1;
      }
    }
    return maxConsecutive;
  };
  // Data fetching
  const fetchEmployeeShifts = async () => {
    try {
      const date = `${year}-${String(month).padStart(2, '0')}-01`;
      const data = await getEmployeeShifts(employeeId, date);
      setEmployeeShifts(data);
      setHasSchedule(data.length === 20);
    } catch (err) {
      console.error('Error fetching schedule:', err);
    }
  };

  const fetchCapacities = async () => {
    try {
      const date = `${year}-${String(month).padStart(2, '0')}-01`;
      console.log('Fetching capacities for next month:', date);
      
      const data = await getShiftCapacities(date);
      setCapacities(data);
    } catch (err) {
      setError('Failed to load shift capacities');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    const fetchData = async () => {
      await fetchCapacities();
      await fetchEmployeeShifts();
    };
    fetchData();
  }, [month, year]);

  // Event handlers
  const handleShiftClick = async (day, shiftType) => {
    if (hasSchedule || !hasAvailability(day, shiftType)) return;
  
    const isSelected = selectedShifts.some(
      s => s.day === day && s.shift_type === shiftType
    );
  
    const date = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
  
    if (isSelected) {
      try {
        // When deselecting, increase available capacity by 1
        await updateShiftCapacity(date, shiftType, 1);
        
        setSelectedShifts(shifts => 
          shifts.filter(s => !(s.day === day && s.shift_type === shiftType))
        );
        
        // Update local capacity state
        const key = `${day}_${shiftType}`;
        setCapacities(prev => ({
          ...prev,
          [key]: {
            ...prev[key],
            available: prev[key].available + 1
          }
        }));
      } catch (err) {
        alert('Failed to update shift capacity. Please try again.');
        return;
      }
      return;
    }
  
    // All existing checks
    if (selectedShifts.some(s => s.day === day)) return;
  
    if (getShiftTypeCount(shiftType) >= 7) {
      alert(`Cannot select more than 7 ${shiftType} shifts`);
      return;
    }
  
    if (selectedShifts.length >= 20) {
      alert('Cannot select more than 20 shifts');
      return;
    }
  
    const newShifts = [...selectedShifts, { day, shift_type: shiftType }];
    if (getConsecutiveDays(newShifts) > 9) {
      alert('Cannot select more than 9 consecutive days');
      return;
    }
  
    try {
      // When selecting, decrease available capacity by 1
      await updateShiftCapacity(date, shiftType, -1);
      
      setSelectedShifts(newShifts);
      
      // Update local capacity state
      const key = `${day}_${shiftType}`;
      setCapacities(prev => ({
        ...prev,
        [key]: {
          ...prev[key],
          available: prev[key].available - 1
        }
      }));
    } catch (err) {
      alert('Failed to update shift capacity. Please try again.');
    }
  };
  
  const handleSubmit = async () => {
    if (selectedShifts.length !== 20) {
      alert('Please select exactly 20 shifts');
      return;
    }
  
    try {
      const formattedShifts = selectedShifts.map(shift => ({
        date: `${year}-${String(month).padStart(2, '0')}-${String(shift.day).padStart(2, '0')}`,
        shift_type: shift.shift_type
      }));
  
      await submitShiftSelections(employeeId, formattedShifts);
      
      // No need to update capacities here since they're already updated during selection
      alert('Shifts submitted successfully!');
      setSelectedShifts([]);
      await fetchCapacities(); // Refresh just to ensure consistency
      await fetchEmployeeShifts();
    } catch (err) {
      alert(err.message || 'Failed to submit shifts. Please try again.');
      // Optionally, you could add capacity rollback here if submission fails
    }
  };

  if (isLoading) {
    return <div className="text-center p-4">Loading...</div>;
  }

  if (error) {
    return <div className="text-center p-4 text-red-600">{error}</div>;
  }

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="mb-6 bg-white rounded-lg shadow-md">
        {/* Enhanced Header Section */}
        <div className="border-b border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Calendar className="h-6 w-6 text-blue-600" />
              <h1 className="text-2xl font-bold text-gray-900">
                {hasSchedule ? 'Your Schedule' : 'Shift Selection'}
              </h1>
            </div>
            <div className="flex items-center space-x-2">
              <Clock className="h-5 w-5 text-gray-500" />
              <span className="text-lg font-medium text-gray-700">
                {getMonthName(month)} {year}
              </span>
            </div>
          </div>

          {!hasSchedule && (
            <div className="mt-4 text-sm text-gray-600">
              Select your preferred shifts for next month. You must select exactly 20 shifts,
              with a maximum of 7 shifts per shift type and no more than 9 consecutive days.
            </div>
          )}
        </div>

        {/* Enhanced Status Cards */}
        {!hasSchedule && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 p-6 border-b border-gray-200">
            <div className="bg-blue-50 rounded-xl p-4 border border-blue-100">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium text-blue-600">Total Selected</div>
                  <div className="mt-1 text-2xl font-bold text-blue-700">
                    {selectedShifts.length}/20
                  </div>
                </div>
                {selectedShifts.length === 20 ? (
                  <CheckCircle className="h-8 w-8 text-blue-500" />
                ) : (
                  <AlertCircle className="h-8 w-8 text-blue-400" />
                )}
              </div>
              <div className="mt-1 text-xs text-blue-600">
                {20 - selectedShifts.length} shifts remaining
              </div>
            </div>

            {shifts.map(shift => (
              <div key={shift.name} 
                   className={`rounded-xl p-4 border ${
                     shift.name === 'Morning' ? 'bg-blue-50 border-blue-100' :
                     shift.name === 'Evening' ? 'bg-orange-50 border-orange-100' :
                     'bg-purple-50 border-purple-100'
                   }`}>
                <div className="flex items-center justify-between">
                  <div>
                    <div className={`text-sm font-medium ${
                      shift.name === 'Morning' ? 'text-blue-600' :
                      shift.name === 'Evening' ? 'text-orange-600' :
                      'text-purple-600'
                    }`}>{shift.name} Shifts</div>
                    <div className={`mt-1 text-2xl font-bold ${
                      shift.name === 'Morning' ? 'text-blue-700' :
                      shift.name === 'Evening' ? 'text-orange-700' :
                      'text-purple-700'
                    }`}>
                      {getShiftTypeCount(shift.name)}/7
                    </div>
                  </div>
                  {getShiftTypeCount(shift.name) === 7 ? (
                    <CheckCircle className={`h-8 w-8 ${
                      shift.name === 'Morning' ? 'text-blue-500' :
                      shift.name === 'Evening' ? 'text-orange-500' :
                      'text-purple-500'
                    }`} />
                  ) : (
                    <Clock className={`h-8 w-8 ${
                      shift.name === 'Morning' ? 'text-blue-400' :
                      shift.name === 'Evening' ? 'text-orange-400' :
                      'text-purple-400'
                    }`} />
                  )}
                </div>
                <div className={`mt-1 text-xs ${
                  shift.name === 'Morning' ? 'text-blue-600' :
                  shift.name === 'Evening' ? 'text-orange-600' :
                  'text-purple-600'
                }`}>
                  {7 - getShiftTypeCount(shift.name)} shifts remaining
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Keep existing calendar grid and buttons */}
        <div className="p-6">
          <div className="grid grid-cols-7 gap-2">
            {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
            <div key={day} className="text-center font-semibold py-2">
              {day}
            </div>
          ))}
          
          {[...Array(firstDayOfMonth)].map((_, i) => (
            <div key={`empty-${i}`} className="aspect-square"></div>
          ))}

          {[...Array(daysInMonth)].map((_, index) => {
            const day = index + 1;
            const employeeShiftForDay = employeeShifts.find(shift => 
              new Date(shift.date).getDate() === day
            );

            return (
              <div key={day} className="border rounded-lg overflow-hidden">
                <div className="text-xs font-semibold p-1 bg-gray-50 border-b">
                  {day}
                </div>
                <div className="flex flex-col h-24">
                  {shifts.map(shift => {
                    const isSelected = selectedShifts.some(
                      s => s.day === day && s.shift_type === shift.name
                    );
                    const isAvailable = !hasSchedule && hasAvailability(day, shift.name);
                    const hasScheduledShift = employeeShiftForDay?.shift_type === shift.name;
                    
                    if (hasSchedule) {
                      // View-only mode stays the same
                      return (
                        <div
                          key={`${day}-${shift.name}`}
                          className={`
                            flex-1 relative cursor-pointer transition-colors
                            ${hasScheduledShift ? shift.color : 'bg-gray-50'} 
                            ${isSelected ? 'ring-2 ring-blue-400 ring-inset' : ''}
                            ${!isAvailable && !hasScheduledShift ? 'opacity-50 cursor-not-allowed' : ''}
                            flex items-center justify-center
                          `}
                        >
                          {hasScheduledShift && (
                            <span className="text-sm font-medium text-gray-800">
                              {shift.name}
                            </span>
                          )}
                        </div>
                      );
                    } else {
                      // Selection mode - Updated
                      // Selection mode - Updated
                      return (
                        <div
                          key={`${day}-${shift.name}`}
                          onClick={() => isAvailable ? handleShiftClick(day, shift.name) : null}
                          className={`
                            flex-1 relative cursor-pointer transition-colors
                            ${shift.color}
                            ${isSelected ? 'ring-2 ring-blue-400 ring-inset' : ''}
                            ${!isAvailable ? 'opacity-50 cursor-not-allowed' : 'hover:brightness-95'}
                            flex items-center justify-center
                          `}
                        >
                          <span className="text-sm font-medium text-gray-800">
                            {shift.name}
                          </span>
                          {!isSelected && (
                            <div 
                              className={`
                                absolute right-2 top-1/2 -translate-y-1/2
                                w-3 h-3 rounded-full
                                ${isAvailable ? 'bg-green-400 shadow-[0_0_4px_rgba(74,222,128,0.5)]' : 'bg-red-400'}
                              `}
                            />
                          )}
                        </div>
                      );
                    }
                  })}
                </div>
              </div>
            );
          })}
          </div>
        </div>
      </div>

      {/* Enhanced Action Buttons */}
      {!hasSchedule && (
        <div className="flex gap-4 justify-end mt-6">
          <button
            onClick={() => setSelectedShifts([])}
            className="px-6 py-2.5 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 
                     transition-colors border border-gray-300 font-medium"
          >
            Clear Selection
          </button>
          <button
            onClick={handleSubmit}
            disabled={selectedShifts.length !== 20}
            className="px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 
                     transition-colors disabled:bg-gray-300 disabled:hover:bg-gray-300 
                     disabled:cursor-not-allowed font-medium flex items-center gap-2"
          >
            <CheckCircle className="h-5 w-5" />
            Submit Selection
          </button>
        </div>
      )}
    </div>
  );
};

export default ShiftSelector;