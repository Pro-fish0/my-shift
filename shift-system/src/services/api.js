const API_URL = 'http://localhost:5000/api';

export const loginUser = async (employeeId, password) => {
    const response = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ employeeId, password }),
    });
    
    if (!response.ok) {
        throw new Error('Login failed');
    }
    
    return response.json();
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

