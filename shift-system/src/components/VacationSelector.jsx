import React, { useState, useEffect } from 'react';
import { Calendar, PalmtreeIcon, CheckCircle, X } from 'lucide-react';
import { requestVacation, getVacationDates } from '../services/api';

const VacationSelector = ({ employeeId, onClose, onVacationSubmitted }) => {
    const [selectedDates, setSelectedDates] = useState([]);
    const [existingVacations, setExistingVacations] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

    // Get next month's date info
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

    // Fetch existing vacations
    useEffect(() => {
        const fetchVacations = async () => {
            try {
                const data = await getVacationDates(employeeId, month, year);
                setExistingVacations(data.map(v => new Date(v.date).getDate()));
            } catch (err) {
                setError('Failed to load existing vacations');
            } finally {
                setIsLoading(false);
            }
        };

        fetchVacations();
    }, [employeeId, month, year]);

    const handleDateClick = (day) => {
        setSelectedDates(prev => {
            const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            if (prev.includes(dateStr)) {
                return prev.filter(d => d !== dateStr);
            }
            return [...prev, dateStr];
        });
    };

    const handleSubmit = async () => {
        if (!selectedDates.length) {
            alert('Please select at least one day for vacation');
            return;
        }

        if (!confirm('This will prevent you from selecting shifts for these days. Continue?')) {
            return;
        }

        try {
            await requestVacation(employeeId, selectedDates);
            alert('Vacation days submitted successfully!');
            if (onVacationSubmitted) {
                onVacationSubmitted();
            }
            onClose();
        } catch (err) {
            alert('Failed to submit vacation days. Please try again.');
        }
    };

    if (isLoading) return <div className="text-center p-4">Loading...</div>;
    if (error) return <div className="text-center p-4 text-red-600">{error}</div>;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center">
            <div className="max-w-4xl w-full bg-white rounded-lg shadow-xl m-4">
                <div className="border-b border-gray-200 p-6">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                            <PalmtreeIcon className="h-6 w-6 text-green-600" />
                            <h1 className="text-2xl font-bold text-gray-900">
                                Vacation Selection
                            </h1>
                        </div>
                        <button
                            onClick={onClose}
                            className="text-gray-400 hover:text-gray-600"
                        >
                            <X className="h-6 w-6" />
                        </button>
                    </div>

                    <div className="mt-4 text-sm text-gray-600">
                        Select the days you would like to take as vacation. 
                        These days will be marked as unavailable for shift selection.
                    </div>
                </div>

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
                            const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
                            const isSelected = selectedDates.includes(dateStr);
                            const isExistingVacation = existingVacations.includes(day);

                            return (
                                <div
                                    key={day}
                                    onClick={() => !isExistingVacation && handleDateClick(day)}
                                    className={`
                                        border rounded-lg overflow-hidden cursor-pointer
                                        ${isExistingVacation ? 'bg-gray-100 cursor-not-allowed' : 'hover:bg-green-50'}
                                        ${isSelected ? 'bg-green-100 ring-2 ring-green-400' : ''}
                                    `}
                                >
                                    <div className="text-xs font-semibold p-1 bg-gray-50 border-b">
                                        {day}
                                    </div>
                                    <div className="h-16 flex items-center justify-center">
                                        {isExistingVacation && (
                                            <span className="text-gray-500">Vacation</span>
                                        )}
                                        {isSelected && (
                                            <CheckCircle className="h-6 w-6 text-green-500" />
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>

                <div className="flex justify-end gap-4 p-6 border-t bg-gray-50">
                    <button
                        onClick={onClose}
                        className="px-6 py-2.5 text-gray-600 hover:text-gray-800 font-medium"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleSubmit}
                        disabled={selectedDates.length === 0}
                        className="px-6 py-2.5 bg-green-600 text-white rounded-lg hover:bg-green-700 
                                 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed font-medium"
                    >
                        Submit Vacation Request
                    </button>
                </div>
            </div>
        </div>
    );
};

export default VacationSelector;