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
CORS(app)


# app = Flask(__name__)
# CORS(app, resources={
#     r"/api/*": {
#         "origins": ["http://127.0.0.1","http://localhost:5173"],
#         "methods": ["GET", "POST", "OPTIONS", "PUT","FETCH"],
#         "allow_headers": ["Content-Type"]
#     }
# })

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shifts.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(10), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)  # Changed from password_hash
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default='employee')
    is_priority = db.Column(db.Boolean, default=False)
    shifts = db.relationship('ShiftSelection', backref='employee_rel', lazy=True)

    def set_password(self, password):
        print(f"Setting password for {self.employee_id}")  # Debug log
        self.password = password  # Store password directly

    def check_password(self, password):
        print(f"Checking password for {self.employee_id}")  # Debug log
        print(f"Stored password: {self.password}")  # Debug log
        print(f"Provided password: {password}")  # Debug log
        return self.password == password  # Direct comparison

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

class VacationRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(10), db.ForeignKey('employee.employee_id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
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
    print(f"Received password: {data.get('password')}")  # Debug log
    
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
        print(f"Fetching shifts and vacations for employee {employee_id}")  # Debug log
        
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

        print(f"Querying between {first_day} and {last_day}")  # Debug log

        # Get all shifts for the employee in this month
        shifts = ShiftSelection.query.filter(
            ShiftSelection.employee_id == str(employee_id),
            ShiftSelection.date >= first_day.date(),
            ShiftSelection.date <= last_day.date()
        ).all()

        # Get all vacations for the employee in this month
        vacations = VacationRequest.query.filter(
            VacationRequest.employee_id == str(employee_id),
            VacationRequest.date >= first_day.date(),
            VacationRequest.date <= last_day.date(),
            VacationRequest.status == 'approved'
        ).all()

        print(f"Found {len(shifts)} shifts and {len(vacations)} vacation days")  # Debug log

        # Format response combining both shifts and vacations
        result = []
        
        # Add shifts
        for shift in shifts:
            # Skip shifts on vacation days
            vacation_dates = [v.date for v in vacations]
            if shift.date not in vacation_dates:
                result.append({
                    'date': shift.date.isoformat(),
                    'shift_type': shift.shift_type,
                    'status': shift.status,
                    'type': 'shift'
                })
        
        # Add vacations
        for vacation in vacations:
            result.append({
                'date': vacation.date.isoformat(),
                'shift_type': 'Vacation',
                'status': 'approved',
                'type': 'vacation'
            })

        # Sort by date
        result.sort(key=lambda x: x['date'])
        
        print(f"Returning {len(result)} total entries")  # Debug log
        return jsonify(result)

    except Exception as e:
        print(f"Error getting employee schedule: {str(e)}")  # Debug log
        return jsonify({'error': str(e)}), 400

@app.route('/api/export/schedule', methods=['GET'])
def export_schedule():
    try:
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)
        
        if not month or not year:
            return jsonify({'error': 'Month and year are required'}), 400

        # Get date range
        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year+1}-01-01"
        else:
            end_date = f"{year}-{month+1:02d}-01"

        # Get all shifts and vacations
        shifts = ShiftSelection.query.filter(
            ShiftSelection.date >= start_date,
            ShiftSelection.date < end_date
        ).all()

        vacations = VacationRequest.query.filter(
            VacationRequest.date >= start_date,
            VacationRequest.date < end_date,
            VacationRequest.status == 'approved'
        ).all()

        # Create CSV header
        csv_data = "Employee_ID"
        for day in range(1, 32):
            csv_data += f",{day}"
        csv_data += "\n"

        # Create a dictionary to store all employee schedules
        schedule_dict = {}

        # Process shifts
        for shift in shifts:
            if shift.employee_id not in schedule_dict:
                schedule_dict[shift.employee_id] = ['O'] * 31
            
            day_index = shift.date.day - 1
            shift_code = 'M' if shift.shift_type == 'Morning' else 'E' if shift.shift_type == 'Evening' else 'N'
            schedule_dict[shift.employee_id][day_index] = shift_code

        # Process vacations (overwrite shifts if any)
        for vacation in vacations:
            if vacation.employee_id not in schedule_dict:
                schedule_dict[vacation.employee_id] = ['O'] * 31
            
            day_index = vacation.date.day - 1
            schedule_dict[vacation.employee_id][day_index] = 'V'

        # Create CSV rows
        for employee_id, schedule in schedule_dict.items():
            csv_data += f"{employee_id},{','.join(schedule)}\n"

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

@app.route('/api/shifts/reset/<employee_id>', methods=['DELETE'])
def reset_shifts(employee_id):
    try:
        # Get parameters from query string instead of request body
        month = int(request.args.get('month'))
        year = int(request.args.get('year'))
        
        if not month or not year:
            return jsonify({'error': 'Month and year are required'}), 400
        
        # Calculate date range
        start_date = datetime(year, month, 1).date()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date()
        else:
            end_date = datetime(year, month + 1, 1).date()

        # Start transaction
        db.session.begin_nested()

        # Delete shifts
        ShiftSelection.query.filter(
            ShiftSelection.employee_id == employee_id,
            ShiftSelection.date >= start_date,
            ShiftSelection.date < end_date
        ).delete(synchronize_session=False)

        db.session.commit()
        return jsonify({'message': 'Shifts reset successfully'})

    except Exception as e:
        db.session.rollback()
        print(f"Error resetting shifts: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/vacation/reset/<employee_id>', methods=['DELETE'])
def reset_vacation(employee_id):
    try:
        # Get parameters from query string instead of request body
        month = int(request.args.get('month'))
        year = int(request.args.get('year'))
        
        if not month or not year:
            return jsonify({'error': 'Month and year are required'}), 400
        
        # Calculate date range
        start_date = datetime(year, month, 1).date()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date()
        else:
            end_date = datetime(year, month + 1, 1).date()

        # Start transaction
        db.session.begin_nested()

        # Delete vacation requests
        VacationRequest.query.filter(
            VacationRequest.employee_id == employee_id,
            VacationRequest.date >= start_date,
            VacationRequest.date < end_date
        ).delete(synchronize_session=False)

        db.session.commit()
        return jsonify({'message': 'Vacation days reset successfully'})

    except Exception as e:
        db.session.rollback()
        print(f"Error resetting vacation: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/users', methods=['GET'])
def get_users():
    try:
        users = Employee.query.all()
        current_month = datetime.now().month + 1  # Next month
        current_year = datetime.now().year
        if current_month > 12:
            current_month = 1
            current_year += 1

        # Format date strings for query
        start_date = f"{current_year}-{str(current_month).zfill(2)}-01"
        if current_month == 12:
            end_date = f"{current_year + 1}-01-01"
        else:
            end_date = f"{current_year}-{str(current_month + 1).zfill(2)}-01"

        user_list = []
        for user in users:
            # Get shift count for next month
            shifts = ShiftSelection.query.filter(
                ShiftSelection.employee_id == user.employee_id,
                ShiftSelection.date >= start_date,
                ShiftSelection.date < end_date
            ).count()

            user_list.append({
                'employeeId': user.employee_id,
                'name': user.name,
                'role': user.role,
                'isPriority': user.is_priority,
                'hasSchedule': shifts == 19  # true if user has full schedule
            })

        return jsonify(user_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/users/<employee_id>', methods=['PUT'])
def update_user(employee_id):
    try:
        data = request.json
        user = Employee.query.filter_by(employee_id=employee_id).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404

        if 'isPriority' in data:
            user.is_priority = data['isPriority']

        db.session.commit()
        return jsonify({'message': 'User updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/users/<employee_id>/reset', methods=['POST'])
def reset_user_schedule(employee_id):
    try:
        # Get month and year from request
        data = request.json
        month = data.get('month', datetime.now().month + 1)  # Default to next month
        year = data.get('year', datetime.now().year)
        
        if month > 12:
            month = 1
            year += 1

        # Calculate date range
        start_date = f"{year}-{str(month).zfill(2)}-01"
        if month == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{str(month + 1).zfill(2)}-01"

        # Delete all shifts for the user in the specified month
        shifts = ShiftSelection.query.filter(
            ShiftSelection.employee_id == employee_id,
            ShiftSelection.date >= start_date,
            ShiftSelection.date < end_date
        ).all()

        for shift in shifts:
            db.session.delete(shift)

        db.session.commit()
        return jsonify({'message': 'Schedule reset successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
@app.route('/api/vacation/request', methods=['POST'])
def request_vacation():
    try:
        data = request.json
        employee_id = data.get('employeeId')
        dates = data.get('dates', [])  # List of dates

        # Convert dates from strings to Date objects and create requests
        for date_str in dates:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            vacation = VacationRequest(
                employee_id=employee_id,
                date=date,
                status='approved'  # Auto-approve for now
            )
            db.session.add(vacation)

        db.session.commit()
        return jsonify({'message': 'Vacation requested successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/vacation/<employee_id>', methods=['GET'])
def get_vacation_dates(employee_id):
    try:
        month = request.args.get('month')
        year = request.args.get('year')
        
        if not month or not year:
            return jsonify({'error': 'Month and year are required'}), 400

        start_date = f"{year}-{month.zfill(2)}-01"
        if int(month) == 12:
            end_date = f"{int(year) + 1}-01-01"
        else:
            end_date = f"{year}-{str(int(month) + 1).zfill(2)}-01"

        vacations = VacationRequest.query.filter(
            VacationRequest.employee_id == employee_id,
            VacationRequest.date >= start_date,
            VacationRequest.date < end_date,
            VacationRequest.status == 'approved'
        ).all()

        return jsonify([{
            'date': vacation.date.isoformat(),
            'status': vacation.status
        } for vacation in vacations])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def init_db():
    with app.app_context():
        db.create_all()
        
        # Check if initialization is done
        if Employee.query.first() is None:  # Simple check if any users exist
            print("Starting database initialization...")
            
            # Add users
            for user in users:
                employee = Employee(
                    employee_id=user['employeeId'],
                    password=user['password'],
                    name=user['name'],
                    role=user['role'],
                    is_priority=user['isPriority']
                )
                db.session.add(employee)
            
            # Add shift capacities
            next_month = datetime.now().replace(day=1) + timedelta(days=32)
            next_month = next_month.replace(day=1)
            
            for day in range(1, 32):
                try:
                    date = next_month.replace(day=day)
                    shifts = [
                        ShiftCapacity(date=date, shift_type='Morning', capacity=12),
                        ShiftCapacity(date=date, shift_type='Evening', capacity=15),
                        ShiftCapacity(date=date, shift_type='Night', capacity=12)
                    ]
                    db.session.add_all(shifts)
                except ValueError:
                    pass
            
            db.session.commit()
            print("Database initialized successfully")
        else:
            print("Database already initialized, skipping...")


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)  # Ensure the server is running on the correct host and port