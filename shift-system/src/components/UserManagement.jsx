import React, { useState, useEffect } from 'react';
import { getUsers, updateUser, resetUserSchedule } from '../services/api';
import { Users, Star, Trash2, AlertCircle, CheckCircle } from 'lucide-react';

const UserManagement = () => {
    const [users, setUsers] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchUsers = async () => {
        try {
            const data = await getUsers();
            setUsers(data);
        } catch (err) {
            setError('Failed to load users');
            console.error(err);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchUsers();
    }, []);

    const handlePriorityToggle = async (employeeId, currentPriority) => {
        try {
            await updateUser(employeeId, { isPriority: !currentPriority });
            await fetchUsers(); // Refresh the list
        } catch (err) {
            alert('Failed to update priority status');
        }
    };

    const handleResetSchedule = async (employeeId) => {
        if (!confirm('Are you sure you want to reset this user\'s schedule? This action cannot be undone.')) {
            return;
        }

        try {
            const nextMonth = new Date().getMonth() + 2;
            const year = nextMonth > 12 ? new Date().getFullYear() + 1 : new Date().getFullYear();
            const month = nextMonth > 12 ? 1 : nextMonth;

            await resetUserSchedule(employeeId, month, year);
            await fetchUsers(); // Refresh the list
            alert('Schedule reset successfully');
        } catch (err) {
            alert('Failed to reset schedule');
        }
    };

    if (isLoading) return <div className="text-center p-4">Loading...</div>;
    if (error) return <div className="text-center p-4 text-red-600">{error}</div>;

    return (
        <div className="max-w-7xl mx-auto p-6">
            <div className="bg-white rounded-lg shadow-md">
                <div className="p-6 border-b border-gray-200">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                            <Users className="h-6 w-6 text-blue-600" />
                            <h1 className="text-2xl font-bold text-gray-900">User Management</h1>
                        </div>
                    </div>
                </div>

                <div className="p-6">
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Employee ID
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Name
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Role
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Status
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Priority
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Actions
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {users.map((user) => (
                                    <tr key={user.employeeId}>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="text-sm font-medium text-gray-900">
                                                {user.employeeId}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="text-sm text-gray-900">{user.name}</div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">
                                                {user.role}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex items-center">
                                                {user.hasSchedule ? (
                                                    <span className="flex items-center text-green-600">
                                                        <CheckCircle className="h-4 w-4 mr-1" />
                                                        Scheduled
                                                    </span>
                                                ) : (
                                                    <span className="flex items-center text-yellow-600">
                                                        <AlertCircle className="h-4 w-4 mr-1" />
                                                        Not Scheduled
                                                    </span>
                                                )}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <button
                                                onClick={() => handlePriorityToggle(user.employeeId, user.isPriority)}
                                                className={`flex items-center px-3 py-1 rounded-full ${
                                                    user.isPriority
                                                        ? 'bg-yellow-100 text-yellow-800'
                                                        : 'bg-gray-100 text-gray-800'
                                                }`}
                                            >
                                                <Star className={`h-4 w-4 mr-1 ${
                                                    user.isPriority ? 'fill-current' : ''
                                                }`} />
                                                {user.isPriority ? 'Priority' : 'Regular'}
                                            </button>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            {user.role !== 'admin' && (
                                                <button
                                                    onClick={() => handleResetSchedule(user.employeeId)}
                                                    className="flex items-center text-red-600 hover:text-red-900"
                                                >
                                                    <Trash2 className="h-4 w-4 mr-1" />
                                                    Reset Schedule
                                                </button>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default UserManagement;