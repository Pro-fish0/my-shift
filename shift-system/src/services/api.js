const API_URL = 'http://127.0.0.1:5000/api';

export const loginUser = async (employeeId, password) => {
    console.log('Attempting login with:', { employeeId }); // Debug log (don't log password)
    
    try {
        const response = await fetch(`${API_URL}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ employeeId, password }),
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            console.error('Login failed:', data); // Debug log
            throw new Error(data.error || 'Login failed');
        }
        
        console.log('Login successful'); // Debug log
        return data;
    } catch (error) {
        console.error('Login error:', error); // Debug log
        throw error;
    }
};

export const getShiftCapacities = async (date) => {
    const response = await fetch(`${API_URL}/shifts/capacity?date=${date}`);
    if (!response.ok) {
        throw new Error('Failed to fetch shift capacities');
    }
    return response.json();
};

export const submitShiftSelections = async (employeeId, shifts) => {
    console.log('Submitting shifts:', { employeeId, shifts }); // Debug log
    
    const response = await fetch(`${API_URL}/shifts/select`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ employeeId, shifts }),
    });

    const data = await response.json();
    
    if (!response.ok) {
        console.error('Server error:', data); // Debug log
        throw new Error(data.error || 'Failed to submit shifts');
    }

    return data;
};
export const setShiftCapacity = async (date, shift_type, capacity) => {
    console.log('API call with:', { date, shift_type, capacity }); // Debug log
    
    const response = await fetch(`${API_URL}/admin/capacity`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            date,
            shift_type,
            capacity: Number(capacity)
        }),
    });
    
    if (!response.ok) {
        const errorData = await response.json();
        console.error('API error:', errorData); // Debug log
        throw new Error(errorData.error || 'Failed to set capacity');
    }
    
    return response.json();
};

export const getEmployeeShifts = async (employeeId, date) => {
    const response = await fetch(`${API_URL}/shifts/employee/${employeeId}?date=${date}`);
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Failed to fetch shifts');
    }
    return response.json();
};


export const exportSchedule = async (month, year) => {
    const response = await fetch(`${API_URL}/export/schedule?month=${month}&year=${year}`, {
        method: 'GET',
        headers: {
            'Accept': 'text/csv'
        }
    });
    
    if (!response.ok) {
        throw new Error('Failed to export schedule');
    }
    
    return response.blob();
};

export const updateShiftCapacity = async (date, shiftType, change) => {
    try {
        console.log('Updating capacity:', { date, shiftType, change }); // Debug log
        
        const response = await fetch(`${API_URL}/shifts/capacity/update`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                date,
                shift_type: shiftType, // Make sure to use shift_type, not shiftType
                change
            }),
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to update shift capacity');
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error in updateShiftCapacity:', error);
        throw error;
    }
};

export const syncUsers = async () => {
    const response = await fetch(`${API_URL}/admin/sync-users`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
    });
    
    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to sync users');
    }
    
    return response.json();
};

export const resetSchedule = async (employeeId, month, year) => {
    try {
        // Use query parameters instead of request body
        const shiftResponse = await fetch(
            `${API_URL}/shifts/reset/${employeeId}?month=${month}&year=${year}`,
            {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                }
            }
        );

        if (!shiftResponse.ok) {
            throw new Error('Failed to reset shifts');
        }

        // Use query parameters for vacation reset as well
        const vacationResponse = await fetch(
            `${API_URL}/vacation/reset/${employeeId}?month=${month}&year=${year}`,
            {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                }
            }
        );

        if (!vacationResponse.ok) {
            throw new Error('Failed to reset vacations');
        }

        return { message: 'Successfully reset schedule and vacations' };
    } catch (error) {
        console.error('Error in resetSchedule:', error);
        throw error;
    }
};

export const getUsers = async () => {
    try {
        const response = await fetch(`${API_URL}/admin/users`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to fetch users');
        }

        return response.json();
    } catch (error) {
        console.error('Error fetching users:', error);
        throw error;
    }
};

export const updateUser = async (employeeId, updates) => {
    try {
        const response = await fetch(`${API_URL}/admin/users/${employeeId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(updates)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to update user');
        }

        return response.json();
    } catch (error) {
        console.error('Error updating user:', error);
        throw error;
    }
};

export const resetUserSchedule = async (employeeId, month, year) => {
    try {
        const response = await fetch(`${API_URL}/admin/users/${employeeId}/reset`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ month, year })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to reset user schedule');
        }

        return response.json();
    } catch (error) {
        console.error('Error resetting user schedule:', error);
        throw error;
    }
};
// Add to api.js

export const requestVacation = async (employeeId, dates) => {
    try {
        const response = await fetch(`${API_URL}/vacation/request`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ employeeId, dates })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to request vacation');
        }

        return response.json();
    } catch (error) {
        console.error('Error requesting vacation:', error);
        throw error;
    }
};

export const getVacationDates = async (employeeId, month, year) => {
    try {
        const response = await fetch(
            `${API_URL}/vacation/${employeeId}?month=${month}&year=${year}`
        );

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to fetch vacation dates');
        }

        return response.json();
    } catch (error) {
        console.error('Error fetching vacation dates:', error);
        throw error;
    }
};