const users = [
    {
        employeeId: "1",
        password: "1",
        name: "John Smith",
        role: "employee",
        isPriority: true
    },
    {
        employeeId: "2",
        password: "2",
        name: "Jane Doe",
        role: "employee",
        isPriority: false
    },
    {
        employeeId: "admin",
        password: "admin",
        name: "Admin User",
        role: "admin",
        isPriority: false
    }
];

export const authenticateUser = (employeeId, password) => {
    const user = users.find(u => u.employeeId === employeeId);
    if (user && user.password === password) {
        // Don't send password to frontend
        const { password, ...userWithoutPassword } = user;
        return userWithoutPassword;
    }
    return null;
};