import { useState, useEffect } from 'react';
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
  const handleShiftClick = (day, shiftType) => {
    if (hasSchedule || !hasAvailability(day, shiftType)) return;

    const isSelected = selectedShifts.some(
      s => s.day === day && s.shift_type === shiftType
    );

    if (isSelected) {
      setSelectedShifts(shifts => 
        shifts.filter(s => !(s.day === day && s.shift_type === shiftType))
      );
      return;
    }

    // Check if day already has a shift
    if (selectedShifts.some(s => s.day === day)) return;

    // Check shift type limit
    if (getShiftTypeCount(shiftType) >= 7) {
      alert(`Cannot select more than 7 ${shiftType} shifts`);
      return;
    }

    // Check total shifts limit
    if (selectedShifts.length >= 20) {
      alert('Cannot select more than 20 shifts');
      return;
    }

    // Check consecutive days
    const newShifts = [...selectedShifts, { day, shift_type: shiftType }];
    if (getConsecutiveDays(newShifts) > 9) {
      alert('Cannot select more than 9 consecutive days');
      return;
    }

    setSelectedShifts(newShifts);
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
      alert('Shifts submitted successfully!');
      setSelectedShifts([]);
      await fetchCapacities();
      await fetchEmployeeShifts();
    } catch (err) {
      alert(err.message || 'Failed to submit shifts. Please try again.');
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
      <div className="mb-6 bg-white rounded-lg shadow-md p-4">
        <h1 className="text-2xl font-bold mb-4">
          {hasSchedule ? 'Your Schedule' : 'Shift Selection'} - {getMonthName(month)} {year}
        </h1>

        {!hasSchedule && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div className="bg-gray-50 p-3 rounded-lg">
              <div className="text-sm text-gray-500">Total Selected</div>
              <div className="text-2xl font-bold">{selectedShifts.length}/20</div>
            </div>
            {shifts.map(shift => (
              <div key={shift.name} className="bg-gray-50 p-3 rounded-lg">
                <div className="text-sm text-gray-500">{shift.name} Shifts</div>
                <div className="text-2xl font-bold">
                  {getShiftTypeCount(shift.name)}/7
                </div>
              </div>
            ))}
          </div>
        )}

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

      {!hasSchedule && (
        <div className="flex gap-4 justify-end">
          <button
            onClick={() => setSelectedShifts([])}
            className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors"
          >
            Clear Selection
          </button>
          <button
            onClick={handleSubmit}
            disabled={selectedShifts.length !== 20}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors
                     disabled:bg-gray-300 disabled:hover:bg-gray-300 disabled:cursor-not-allowed"
          >
            Submit Selection
          </button>
        </div>
      )}
    </div>
  );
};

export default ShiftSelector;