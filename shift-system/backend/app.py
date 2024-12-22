from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask import send_file
import csv
from io import StringIO
from flask import make_response  # Add this import
import json
import os
import re




app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://209.38.41.138","http://127.0.0.1","http://localhost:5173"],
        "methods": ["GET", "POST", "OPTIONS", "PUT"],
        "allow_headers": ["Content-Type"]
    }
})
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shifts.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(10), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default='employee')
    is_priority = db.Column(db.Boolean, default=False)
    shifts = db.relationship('ShiftSelection', backref='employee_rel', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class ShiftCapacity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    shift_type = db.Column(db.String(20), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('date', 'shift_type'),
    )

class ShiftSelection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(10), db.ForeignKey('employee.employee_id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    shift_type = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='approved')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('employee_id', 'date'),
    )

# Load users from users.js
def load_users():
    with open(os.path.join(os.path.dirname(__file__), '../src/data/users.js')) as f:
        content = f.read()
        users_data = re.search(r'export const users = (\[.*?\]);', content, re.DOTALL).group(1)
        
        # Convert JavaScript object to valid JSON
        users_data = users_data.replace("'", '"')  # Replace single quotes with double quotes
        users_data = re.sub(r'(\w+):', r'"\1":', users_data)  # Add quotes around property names
        users_data = re.sub(r',\s*}', '}', users_data)  # Remove trailing commas
        users_data = re.sub(r',\s*]', ']', users_data)  # Remove trailing commas in arrays
        
        try:
            return json.loads(users_data)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            print(f"Problematic JSON: {users_data[:100]}...")  # Print first 100 chars for debugging
            raise

users = load_users()

#API Routes
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    print(f"Login attempt for employee ID: {data.get('employeeId')}")  # Debug log
    employee = Employee.query.filter_by(employee_id=data.get('employeeId')).first()
    
    if employee:
        print(f"Employee found: {employee.name}")  # Debug log
        if employee.check_password(data.get('password')):
            print("Password check passed")  # Debug log
            return jsonify({
                'user': {
                    'employeeId': employee.employee_id,
                    'name': employee.name,
                    'role': employee.role,
                    'isPriority': employee.is_priority
                }
            })
        else:
            print("Password check failed")  # Debug log
    else:
        print("Employee not found")  # Debug log
    
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/shifts/capacity', methods=['GET'])
def get_capacities():
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({'error': 'Date parameter is required'}), 400
    
    try:
        # Parse the input date
        query_date = datetime.strptime(date_str, '%Y-%m-%d')
        
        # Get first and last day of the requested month
        first_day = datetime(query_date.year, query_date.month, 1)
        
        # For last day, if next month is January, increment year
        if query_date.month == 12:
            last_day = datetime(query_date.year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = datetime(query_date.year, query_date.month + 1, 1) - timedelta(days=1)

        print(f"Fetching capacities for {query_date.year}-{query_date.month:02d}")
        print(f"Date range: {first_day.date()} to {last_day.date()}")
        
        # Get all capacities for the month
        capacities = ShiftCapacity.query.filter(
            ShiftCapacity.date >= first_day.date(),
            ShiftCapacity.date <= last_day.date()
        ).all()

        # Get all selected shifts for the month
        selected_shifts = ShiftSelection.query.filter(
            ShiftSelection.date >= first_day.date(),
            ShiftSelection.date <= last_day.date(),
            ShiftSelection.status == 'approved'
        ).all()

        # Count selected shifts by date and type
        shift_counts = {}
        for shift in selected_shifts:
            key = f"{shift.date.day}_{shift.shift_type}"
            shift_counts[key] = shift_counts.get(key, 0) + 1

        # Build response with actual availability
        result = {}
        for capacity in capacities:
            key = f"{capacity.date.day}_{capacity.shift_type}"
            taken = shift_counts.get(key, 0)
            result[key] = {
                'total': capacity.capacity,
                'taken': taken,
                'available': capacity.capacity - taken
            }
        
        print(f"Returning {len(result)} capacity records")
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in get_capacities: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/admin/capacity', methods=['POST'])
def set_capacity():
    try:
        data = request.json
        print("Received data:", data)  # Debug log
        
        date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        capacity = int(data['capacity'])
        shift_type = data['shift_type']
        
        # Get or create capacity record
        capacity_record = ShiftCapacity.query.filter_by(
            date=date,
            shift_type=shift_type
        ).first()

        if capacity_record:
            print(f"Updating existing capacity: {capacity_record.capacity} -> {capacity}")  # Debug log
            capacity_record.capacity = capacity
        else:
            print(f"Creating new capacity record: {capacity}")  # Debug log
            capacity_record = ShiftCapacity(
                date=date,
                shift_type=shift_type,
                capacity=capacity
            )
            db.session.add(capacity_record)

        db.session.commit()
        
        # Verify the data was saved
        verification = ShiftCapacity.query.filter_by(
            date=date,
            shift_type=shift_type
        ).first()
        print(f"Verified saved capacity: {verification.capacity}")  # Debug log
        
        return jsonify({
            'message': 'Capacity updated successfully',
            'data': {
                'date': date.isoformat(),
                'shift_type': shift_type,
                'capacity': capacity
            }
        })

    except Exception as e:
        db.session.rollback()
        print(f"Error in set_capacity: {str(e)}")  # Debug log
        return jsonify({'error': str(e)}), 400
    
@app.route('/api/shifts/select', methods=['POST'])
def select_shifts():
    try:
        data = request.json
        print("Received shift selection data:", data)
        
        employee_id = data.get('employeeId')
        shifts = data.get('shifts', [])

        if not employee_id:
            return jsonify({'error': 'Employee ID is required'}), 400

        if len(shifts) != 19:
            return jsonify({'error': 'Must select exactly 19 shifts'}), 400

        # Start a single transaction for the entire operation
        db.session.begin()
        
        try:
            # First validate all shifts
            for shift in shifts:
                date = datetime.strptime(shift['date'], '%Y-%m-%d').date()
                
                # Check if employee already has a shift on this date
                existing_shift = ShiftSelection.query.filter_by(
                    employee_id=employee_id,
                    date=date
                ).first()
                
                if existing_shift:
                    db.session.rollback()
                    return jsonify({'error': f'You already have a shift scheduled for {date}'}), 400

                # Check capacity
                capacity = ShiftCapacity.query.filter_by(
                    date=date,
                    shift_type=shift['shift_type']
                ).first()

                if not capacity:
                    db.session.rollback()
                    return jsonify({'error': f'No capacity set for {date} {shift["shift_type"]}'}), 400

                current_selections = ShiftSelection.query.filter_by(
                    date=date,
                    shift_type=shift['shift_type'],
                    status='approved'
                ).count()

                if current_selections >= capacity.capacity:
                    db.session.rollback()
                    return jsonify({'error': f'No capacity available for {date} {shift["shift_type"]}'}), 400

            # All validations passed, now insert the shifts
            for shift in shifts:
                date = datetime.strptime(shift['date'], '%Y-%m-%d').date()
                new_selection = ShiftSelection(
                    employee_id=employee_id,
                    date=date,
                    shift_type=shift['shift_type'],
                    status='approved'
                )
                db.session.add(new_selection)

            # Commit the transaction
            db.session.commit()
            return jsonify({'message': 'Shifts selected successfully'})
            
        except Exception as e:
            db.session.rollback()
            raise e

    except Exception as e:
        print(f"Error in select_shifts: {str(e)}")
        return jsonify({'error': str(e)}), 400
    
@app.route('/api/shifts/employee/<employee_id>', methods=['GET'])
def get_employee_shifts(employee_id):
    try:
        print(f"Fetching shifts for employee {employee_id}")  # Debug log
        
        # Get date parameter
        date = request.args.get('date')
        if not date:
            return jsonify({'error': 'Date parameter is required'}), 400

        print(f"Date parameter: {date}")  # Debug log
        
        # Parse date and get month range
        query_date = datetime.strptime(date, '%Y-%m-%d')
        first_day = query_date.replace(day=1)
        if first_day.month == 12:
            last_day = datetime(first_day.year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = datetime(first_day.year, first_day.month + 1, 1) - timedelta(days=1)

        print(f"Querying shifts between {first_day} and {last_day}")  # Debug log

        # Get all shifts for the employee in this month
        shifts = ShiftSelection.query.filter(
            ShiftSelection.employee_id == str(employee_id),
            ShiftSelection.date >= first_day.date(),
            ShiftSelection.date <= last_day.date()
        ).all()

        # Format shifts for response
        result = []
        for shift in shifts:
            result.append({
                'date': shift.date.isoformat(),
                'shift_type': shift.shift_type,
                'status': shift.status
            })

        print(f"Found {len(result)} shifts")  # Debug log
        return jsonify(result)

    except Exception as e:
        print(f"Error getting employee shifts: {str(e)}")  # Debug log
        return jsonify({'error': str(e)}), 400

@app.route('/api/export/schedule', methods=['GET'])
def export_schedule():
    try:
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)
        
        if not month or not year:
            return jsonify({'error': 'Month and year are required'}), 400

        # Get all shifts for the month
        shifts = ShiftSelection.query.filter(
            ShiftSelection.date >= f"{year}-{month:02d}-01",
            ShiftSelection.date < f"{year}-{month+1:02d}-01" if month < 12 else f"{year+1}-01-01"
        ).order_by(ShiftSelection.employee_id, ShiftSelection.date).all()

        # Create CSV data
        csv_data = "Employee_ID"
        for day in range(1, 32):
            csv_data += f",{day}"
        csv_data += "\n"

        current_employee = None
        day_shifts = []

        for shift in shifts:
            if current_employee != shift.employee_id:
                if current_employee is not None:
                    while len(day_shifts) < 31:
                        day_shifts.append('O')
                    csv_data += f"{current_employee},{','.join(day_shifts)}\n"
                current_employee = shift.employee_id
                day_shifts = ['O'] * 31

            day_index = shift.date.day - 1
            shift_code = 'M' if shift.shift_type == 'Morning' else 'E' if shift.shift_type == 'Evening' else 'N'
            day_shifts[day_index] = shift_code

        # Add last employee's data
        if current_employee is not None:
            while len(day_shifts) < 31:
                day_shifts.append('O')
            csv_data += f"{current_employee},{','.join(day_shifts)}\n"

        # Create response
        response = make_response(csv_data)
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=schedule_{year}_{month}.csv'
        return response

    except Exception as e:
        print(f"Error exporting schedule: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/shifts/capacity/update', methods=['PUT'])
def update_shift_capacity():
    try:
        data = request.json
        print("Received capacity update data:", data)  # Debug log
        
        date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        shift_type = data['shift_type']
        change = data['change']

        # Get the capacity record
        capacity = ShiftCapacity.query.filter_by(
            date=date,
            shift_type=shift_type
        ).first()

        if not capacity:
            return jsonify({'error': 'Capacity record not found'}), 404

        # Get current number of selections
        selections = ShiftSelection.query.filter_by(
            date=date,
            shift_type=shift_type,
            status='approved'
        ).count()

        # Calculate new selections count
        new_selections = selections + (change * -1)  # Negative change means adding a selection

        if new_selections < 0 or new_selections > capacity.capacity:
            return jsonify({'error': 'Invalid capacity change'}), 400

        # Return updated capacity info with more details
        return jsonify({
            'success': True,
            'total': capacity.capacity,
            'taken': new_selections,
            'available': capacity.capacity - new_selections,
            'date': date.isoformat(),
            'shift_type': shift_type
        })

    except Exception as e:
        print(f"Error updating capacity: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/admin/sync-users', methods=['POST'])
def sync_users():
    try:
        # Reload users from file
        global users
        users = load_users()
        
        # Add new users to database
        for user in users:
            employee = Employee.query.filter_by(employee_id=user['employeeId']).first()
            if not employee:
                new_employee = Employee(
                    employee_id=user['employeeId'],
                    name=user['name'],
                    role=user['role'],
                    is_priority=user['isPriority']
                )
                new_employee.set_password(user['password'])
                db.session.add(new_employee)
        
        db.session.commit()
        return jsonify({'message': 'Users synchronized successfully'})
    
    except Exception as e:
        db.session.rollback()
        print(f"Error syncing users: {str(e)}")
        return jsonify({'error': str(e)}), 500

def init_db():
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        
        # Sync users
        if not Employee.query.first():
            for user in users:
                employee = Employee(
                    employee_id=user['employeeId'],
                    name=user['name'],
                    role=user['role'],
                    is_priority=user['isPriority']
                )
                employee.set_password(user['password'])
                db.session.add(employee)
            
            db.session.commit()

            # Create sample shift capacities for the next month
            next_month = datetime.now().replace(day=1) + timedelta(days=32)
            next_month = next_month.replace(day=1)
            
            for day in range(1, 32):
                try:
                    date = next_month.replace(day=day)
                    shifts = [
                        ShiftCapacity(date=date, shift_type='Morning', capacity=12),
                        ShiftCapacity(date=date, shift_type='Evening', capacity=14),
                        ShiftCapacity(date=date, shift_type='Night', capacity=12)
                    ]
                    db.session.add_all(shifts)
                except ValueError:
                    pass
            
            db.session.commit()


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)