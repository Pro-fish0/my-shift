from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask import send_file
import csv
from io import StringIO
from flask import make_response  # Add this import


# app = Flask(__name__)
# CORS(app)

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# CORS(app, resources={
#     r"/api/*": {
#         "origins": ["http://209.38.41.138"],
#         "methods": ["GET", "POST", "OPTIONS"],
#         "allow_headers": ["Content-Type"]
#     }
# })
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

#API Routes
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    employee = Employee.query.filter_by(employee_id=data.get('employeeId')).first()
    
    if employee and employee.check_password(data.get('password')):
        return jsonify({
            'user': {
                'employeeId': employee.employee_id,
                'name': employee.name,
                'role': employee.role,
                'isPriority': employee.is_priority
            }
        })
    
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

        if len(shifts) != 20:
            return jsonify({'error': 'Must select exactly 20 shifts'}), 400

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
    
# Initialize database
def init_db():
    with app.app_context():
        # Drop and recreate all tables
        db.drop_all()
        db.create_all()
        
        # Add sample data if database is empty
        if not Employee.query.first(): 
            # Create sample employees
            admin = Employee(
                employee_id='33333',
                name='admin',
                role='admin',
                is_priority=False
            )
            admin.set_password('admin')
            
            emp1 = Employee(
                employee_id='11246',
                name='Lama Eidha Manaa Al-Khdeidi',
                role='employee',
                is_priority=False
            )
            emp1.set_password('L11246')
            
            emp2 = Employee(
                employee_id='11249',
                name='Hatim Bakheit Muqbil Al-Daadi',
                role='employee',
                is_priority=False
            )
            emp2.set_password('H11249')
            
            emp3 = Employee(
                employee_id='11253',
                name='Abdullah Hassan Salem Al-Talhi',
                role='employee',
                is_priority=False
            )
            emp3.set_password('A11253')
            
            emp4 = Employee(
                employee_id='11254',
                name='Salem Hassan Salem Al-Talhi',
                role='employee',
                is_priority=False
            )
            emp4.set_password('S11254')
            
            emp5 = Employee(
                employee_id='11257',
                name='Hadeel Ibrahim Barik Al-Mawlid',
                role='employee',
                is_priority=False
            )
            emp5.set_password('H11257')
            
            emp6 = Employee(
                employee_id='11284',
                name='Harith Abdullah Raziq Al-Hazmi',
                role='employee',
                is_priority=False
            )
            emp6.set_password('H11284')
            
            emp7 = Employee(
                employee_id='11300',
                name='Yazan Ibrahim Eidha Al-Jaidi',
                role='employee',
                is_priority=False
            )
            emp7.set_password('Y11300')
            
            emp8 = Employee(
                employee_id='100094',
                name='Falwah Khalid Eidha Al-Nufai',
                role='employee',
                is_priority=False
            )
            emp8.set_password('F100094')
            
            emp9 = Employee(
                employee_id='100100',
                name='Ghada Mohammed Maadh Al-Shahri',
                role='employee',
                is_priority=False
            )
            emp9.set_password('G100100')
            
            emp10 = Employee(
                employee_id='100104',
                name='Abdullah Ali Ahmed Al-Sharif',
                role='employee',
                is_priority=False
            )
            emp10.set_password('A100104')
            
            emp11 = Employee(
                employee_id='100108',
                name='Shawq Abdullah Madi Khal Al-Mutairi',
                role='employee',
                is_priority=False
            )
            emp11.set_password('S100108')
            
            emp12 = Employee(
                employee_id='100111',
                name='Ghadir Aayed Odeh Al-Dhubaiani',
                role='employee',
                is_priority=False
            )
            emp12.set_password('G100111')
            
            emp13 = Employee(
                employee_id='11247',
                name='Ghassan Habib Mohammed Hawasawi',
                role='employee',
                is_priority=False
            )
            emp13.set_password('G11247')
            
            emp14 = Employee(
                employee_id='11248',
                name='Riham Adnan Jamil Ramadan',
                role='employee',
                is_priority=False
            )
            emp14.set_password('R11248')
            
            emp15 = Employee(
                employee_id='11267',
                name='Osama Mohammed Ali Bahadad',
                role='employee',
                is_priority=False
            )
            emp15.set_password('O11267')
            
            emp16 = Employee(
                employee_id='11283',
                name='Ahmed Mohsen Mohammed Al-Suhimi',
                role='employee',
                is_priority=False
            )
            emp16.set_password('A11283')
            
            emp17 = Employee(
                employee_id='11287',
                name='Fahd Mohammed Omar Al-Sufyani',
                role='employee',
                is_priority=False
            )
            emp17.set_password('F11287')
            
            emp18 = Employee(
                employee_id='11303',
                name='Waleed Khalid Saeed Barhim',
                role='employee',
                is_priority=False
            )
            emp18.set_password('W11303')
            
            emp19 = Employee(
                employee_id='100001',
                name='Ahmed Mohammed Ahmed Al-Amari',
                role='employee',
                is_priority=False
            )
            emp19.set_password('A100001')
            
            emp20 = Employee(
                employee_id='100005',
                name='Manal Saad Zaid Al-Buqami',
                role='employee',
                is_priority=False
            )
            emp20.set_password('M100005')
            
            emp21 = Employee(
                employee_id='100102',
                name='Rana Awad Eid Al-Sawat',
                role='employee',
                is_priority=False
            )
            emp21.set_password('R100102')
            
            emp22 = Employee(
                employee_id='100107',
                name='Thuraya Mohammed Ahmed Shomali',
                role='employee',
                is_priority=False
            )
            emp22.set_password('T100107')
            
            emp23 = Employee(
                employee_id='100112',
                name='Maha Maadh Awad Al-Zahrani',
                role='employee',
                is_priority=False
            )
            emp23.set_password('M100112')
            
            emp24 = Employee(
                employee_id='100113',
                name='Lamia Saud Yahya Al-Ghamdi',
                role='employee',
                is_priority=False
            )
            emp24.set_password('L100113')
            
            emp25 = Employee(
                employee_id='11250',
                name='Thamer Jaber Habab Al-Nufai',
                role='employee',
                is_priority=False
            )
            emp25.set_password('T11250')
            
            emp26 = Employee(
                employee_id='11256',
                name='Adel Ali Mahdi Al-Shahri',
                role='employee',
                is_priority=False
            )
            emp26.set_password('A11256')
            
            emp27 = Employee(
                employee_id='11260',
                name='Marwa Mohammed Musa Hussein',
                role='employee',
                is_priority=False
            )
            emp27.set_password('M11260')
            
            emp28 = Employee(
                employee_id='11265',
                name='Tahani Matar Qashimah Al-Hudhali',
                role='employee',
                is_priority=False
            )
            emp28.set_password('T11265')
            
            emp29 = Employee(
                employee_id='11266',
                name='Asma Mohammed Naseeb Al-Zahrani',
                role='employee',
                is_priority=False
            )
            emp29.set_password('A11266')
            
            emp30 = Employee(
                employee_id='11285',
                name='Khalid Aliwi Ali Al-Qurashi',
                role='employee',
                is_priority=False
            )
            emp30.set_password('K11285')
            
            emp31 = Employee(
                employee_id='11289',
                name='Nouf Jalal Marzouq Al-Khdeidi',
                role='employee',
                is_priority=False
            )
            emp31.set_password('N11289')
            
            emp32 = Employee(
                employee_id='11292',
                name='Bayan Mohammed Mahmoud Al-Sabhi',
                role='employee',
                is_priority=False
            )
            emp32.set_password('B11292')
            
            emp33 = Employee(
                employee_id='11293',
                name='Maher Abdullah Atiq Al-Muhmadi',
                role='employee',
                is_priority=False
            )
            emp33.set_password('M11293')
            
            emp34 = Employee(
                employee_id='100013',
                name='Iman Qasim Jamal Khan',
                role='employee',
                is_priority=False
            )
            emp34.set_password('I100013')
            
            emp35 = Employee(
                employee_id='100091',
                name='Dania Samir Abdulghani Maqliya',
                role='employee',
                is_priority=False
            )
            emp35.set_password('D100091')
            
            emp36 = Employee(
                employee_id='100101',
                name='Heba Mohammed Harmeen Mandeel',
                role='employee',
                is_priority=False
            )
            emp36.set_password('H100101')
            
            emp37 = Employee(
                employee_id='100103',
                name='Hajar Hassan Saleh Al-Zahrani',
                role='employee',
                is_priority=False
            )
            emp37.set_password('H100103')
            
            emp38 = Employee(
                employee_id='11244',
                name='Mohammed Abdulrahman Mohammed Al-Qarni',
                role='employee',
                is_priority=False
            )
            emp38.set_password('M11244')
            
            emp39 = Employee(
                employee_id='11251',
                name='Ashwaq Majid Dheef Allah Al-Harbi',
                role='employee',
                is_priority=False
            )
            emp39.set_password('A11251')
            
            emp40 = Employee(
                employee_id='11258',
                name='Bashayer Sami Salem Ghandoura',
                role='employee',
                is_priority=False
            )
            emp40.set_password('B11258')
            
            emp41 = Employee(
                employee_id='11259',
                name='Dalia Samir Ali Ashour',
                role='employee',
                is_priority=False
            )
            emp41.set_password('D11259')
            
            emp42 = Employee(
                employee_id='11262',
                name='Anbar Mabrook Saad Al-Harbi',
                role='employee',
                is_priority=False
            )
            emp42.set_password('A11262')
            
            emp43 = Employee(
                employee_id='11263',
                name='Abdullah Awad Saeed Al-Ghamdi',
                role='employee',
                is_priority=False
            )
            emp43.set_password('A11263')
            
            emp44 = Employee(
                employee_id='11268',
                name='Mansour Ahmed Ayesh Al-Zanini',
                role='employee',
                is_priority=False
            )
            emp44.set_password('M11268')
            
            emp45 = Employee(
                employee_id='11269',
                name='Majed Ali Salem Al-Harthi',
                role='employee',
                is_priority=False
            )
            emp45.set_password('M11269')
            
            emp46 = Employee(
                employee_id='11301',
                name='Maram Abdullah Abdulrahman Al-Jafri',
                role='employee',
                is_priority=False
            )
            emp46.set_password('M11301')
            
            emp47 = Employee(
                employee_id='11433',
                name='Mohammed Abdulhafiz Ibrahim Al-Falati',
                role='employee',
                is_priority=False
            )
            emp47.set_password('M11433')
            
            emp48 = Employee(
                employee_id='100098',
                name='Lujain Saeed Ahmed Al-Bashri',
                role='employee',
                is_priority=False
            )
            emp48.set_password('L100098')
            
            emp49 = Employee(
                employee_id='100099',
                name='Rehab Aaidh Sattar Al-Jaidi',
                role='employee',
                is_priority=False
            )
            emp49.set_password('R100099')
            
            emp50 = Employee(
                employee_id='100110',
                name='Shifa Shukri Ahmed Abdulraouf',
                role='employee',
                is_priority=False
            )
            emp50.set_password('S100110')
            
            emp51 = Employee(
                employee_id='11242',
                name='Faris Abdullah Maeesh Al-Otaibi',
                role='employee',
                is_priority=False
            )
            emp51.set_password('F11242')
            
            emp52 = Employee(
                employee_id='11245',
                name='Mohammed Khalid Radad Al-Harthi',
                role='employee',
                is_priority=False
            )
            emp52.set_password('M11245')
            
            emp53 = Employee(
                employee_id='11261',
                name='Abeer Ibrahim Maadh Al-Zahrani',
                role='employee',
                is_priority=False
            )
            emp53.set_password('A11261')
            
            emp54 = Employee(
                employee_id='11270',
                name='Abdulilah Osman Hadi Ayoub',
                role='employee',
                is_priority=False
            )
            emp54.set_password('A11270')
            
            emp55 = Employee(
                employee_id='11288',
                name='Worood Batieh Maawad Al-Hudhali',
                role='employee',
                is_priority=False
            )
            emp55.set_password('W11288')
            
            emp56 = Employee(
                employee_id='11291',
                name='Wadyan Saleh Ghrom Allah Al-Ghamdi',
                role='employee',
                is_priority=False
            )
            emp56.set_password('W11291')
            
            emp57 = Employee(
                employee_id='11302',
                name='Abdulmohsen Suhail Habab Al-Otaibi',
                role='employee',
                is_priority=False
            )
            emp57.set_password('A11302')
            
            emp58 = Employee(
                employee_id='100092',
                name='Asma Turki Hamoud Al-Harbi',
                role='employee',
                is_priority=False
            )
            emp58.set_password('A100092')
            
            emp59 = Employee(
                employee_id='100093',
                name='Mohammed Saeed Massoud Al-Harbi',
                role='employee',
                is_priority=False
            )
            emp59.set_password('M100093')
            
            emp60 = Employee(
                employee_id='100095',
                name='Reem Naji Abdulaziz Al-Ahmadi',
                role='employee',
                is_priority=False
            )
            emp60.set_password('R100095')
            
            emp61 = Employee(
                employee_id='100096',
                name='Fatimah Adlan Hasan Al-Shamrani',
                role='employee',
                is_priority=False
            )
            emp61.set_password('F100096')
            
            emp62 = Employee(
                employee_id='100097',
                name='Abdullah Mohammed Eid Al-Otaibi',
                role='employee',
                is_priority=False
            )
            emp62.set_password('A100097')
            
            emp63 = Employee(
                employee_id='100109',
                name='Omnia Fawaz Talal Murad',
                role='employee',
                is_priority=False
            )
            emp63.set_password('A100109')
            
            # Add all employees to the session
            db.session.add_all([
                admin
            ])
            
            # Commit the session to save the employees to the database
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
                    # Skip invalid dates (e.g., February 31)
                    pass
            
            db.session.commit()

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)