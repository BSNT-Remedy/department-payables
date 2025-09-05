import os
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc, asc, func
import webview
from threading import Thread
import logging
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__, template_folder='templates')
app.secret_key = "sikretongmalupet"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.sqlite3'
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['DEBUG'] = True
app.config['UPLOAD_FOLDER'] = 'static/uploads'  # Folder for image uploads
logging.basicConfig(filename='app_error.log', level=logging.DEBUG)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

student_payable = db.Table('student_payable',
    db.Column('student_id', db.Integer, db.ForeignKey('student.id')),
    db.Column('payable_id', db.Integer, db.ForeignKey('payable.id'))
)

class StudentPayable(db.Model):
    __tablename__ = 'student_payables'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))
    payable_id = db.Column(db.Integer, db.ForeignKey('payable.id'))
    quantity = db.Column(db.Integer, nullable=False, default=1)
    is_paid = db.Column(db.Boolean, default=False)
    semester = db.Column(db.String, nullable=False)
    student = db.relationship("Student", back_populates="student_payables")
    payable = db.relationship("Payable", back_populates="student_payables")

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_number = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    contactNum = db.Column(db.String(11), default='N/A')
    contactPerson = db.Column(db.String(100), default='N/A')
    address = db.Column(db.String(200), default='N/A')
    department = db.Column(db.String(50), nullable=False)
    status = db.Column(db.Boolean, nullable=False)
    image_path = db.Column(db.String(200), nullable=True)  # New field for image path
    student_payables = db.relationship("StudentPayable", back_populates="student", cascade="all, delete-orphan")
    payments = db.relationship("Payment", back_populates="student", cascade="all, delete-orphan")

class Payable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    payable_name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String, nullable=False)
    payable_department = db.Column(db.String, nullable=False)
    payable_tax = db.Column(db.Float, default=0)
    student_payables = db.relationship("StudentPayable", back_populates="payable", cascade="all, delete-orphan")

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    amount_paid = db.Column(db.Float, nullable=False)
    semester_payment = db.Column(db.String, nullable=False)
    is_fully_paid = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    student = db.relationship("Student", back_populates="payments")

class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    department_name = db.Column(db.String(100), nullable=False, unique=True)
    department_tax = db.Column(db.Float, default=50.0)

    courses = db.relationship('Course', backref='department', lazy=True)

class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    course_name = db.Column(db.String(100), nullable=False)

    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)

def generate_student_number(year_entered, course):
    last_student = Student.query.filter(Student.student_number.like(f'{year_entered[-2:]}-0%'), Student.student_number.like(f'%-{course}-%')).order_by(Student.student_number.desc()).first()
    next_id = 1 if last_student is None else int(last_student.student_number[-2:]) + 1
    year = year_entered[-2:]
    return f"{year}-{course}-{next_id:02d}"

@app.route('/')
def index():
    try:
        return redirect(url_for("login"))
    except Exception as e:
        logging.error(f"Error in route: {str(e)}")
        return "Internal Server Error", 500

@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        usr = request.form.get('username')
        pw = request.form.get('password')
        if usr == "msM" and pw == "143ccs":
            return redirect(url_for("dept"))
        elif usr == "tcc" and pw == "143tcc":
            return redirect(url_for("dept"))
        else:
            return render_template("Flogin.html", InvalidAccount=True)
    return render_template("Flogin.html")

@app.route("/dept", methods=["POST", "GET"])
def dept():
    if request.method == "POST":
        selected_department = request.form.get("selectedDepartment")
        session["selectedDepartment"] = selected_department
        if session.get("selectedSemester") or request.form.get("selectedSemester"):
            return redirect(url_for("students"))
        else:
            return redirect(url_for("semesters"))
    return render_template("dept.html")

@app.route("/semesters", methods=["POST", "GET"])
def semesters():
    current_year = datetime.now().year
    if request.method == "POST":
        selected_school_year = request.form.get("selectedSchoolYear")
        selected_sem = request.form.get("selectedSem")

        selected_semester = selected_school_year + selected_sem
        session["selectedSemester"] = selected_semester
        return redirect(url_for("students"))
    return render_template("semesters.html", current_year=current_year)

@app.route("/students", methods=["GET", "POST"])
def students():
    selectedDepartment = session.get("selectedDepartment") or request.form.get("selectedDepartment")
    selected_semester = session.get("selectedSemester") or request.form.get("selectedSemester")
    max_year = int(datetime.now().year) + 10

    if selectedDepartment:
        is_existing_department = Department.query.filter_by(department_name=selectedDepartment).first()
        if not is_existing_department:
            try:
                new_department = Department(department_name=selectedDepartment)
                db.session.add(new_department)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                logging.error(f"Error adding department: {str(e)}")

    alldepartments = Department.query.all()

    current_first_year = int(selected_semester[2:4])

    year = request.args.get('year')
    if year == "01":
        students_year = Student.query.filter(Student.department == selectedDepartment,
                                             Student.status == False).order_by(
            Student.student_number).all()
    elif year:
        students_year = Student.query.filter(Student.department == selectedDepartment,
                                             Student.status == True,
                                             Student.student_number.startswith(year)).order_by(
            Student.student_number).all()
    else:
        last_student = Student.query.filter(
            Student.department == selectedDepartment, Student.status == True
        ).order_by(Student.id.desc()).first()

        if last_student:
            latest_year = last_student.student_number[:2]
            students_year = Student.query.filter(
                Student.department == selectedDepartment,
                Student.student_number.startswith(latest_year),
                Student.status == True
            ).order_by(Student.student_number).all()
        else:
            students_year = []
    allstudents = Student.query.filter(Student.department == selectedDepartment).order_by(
        desc(func.substr(Student.student_number, 1, 2)), asc(func.substr(Student.student_number, 4, 2)),
        asc(func.substr(Student.student_number, 7, 2))).all()

    if request.method == "POST":
        data = request.form
        new_student_name = data.get("nm")
        year_entered = data.get("yearEntered")
        course = data.get("course")
        status = data.get("student_status")
        if not (new_student_name and year_entered and course):
            flash("Fields cannot be empty.", "error")
            return redirect(url_for("students"))
        new_student = Student(
            student_number=generate_student_number(year_entered, course),
            name=new_student_name,
            contactNum=data.get("contactNum", "N/A").strip() or "N/A",
            contactPerson=data.get("contactPerson", "N/A").strip() or "N/A",
            address=data.get("address", "N/A").strip() or "N/A",
            department=selectedDepartment,
            status= bool(int(status))
        )
        # Handle image upload
        image_file = request.files.get('image')
        if image_file and image_file.filename:
            try:
                filename = secure_filename(image_file.filename)
                # Create a unique filename to avoid conflicts
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                unique_filename = f"{timestamp}_{filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                image_file.save(file_path)
                new_student.image_path = f"uploads/{unique_filename}"
            except Exception as e:
                db.session.rollback()
                logging.error(f"Error saving image for student {new_student_name}: {str(e)}")
                flash(f"Error saving image: {str(e)}", "error")
                return redirect(url_for("students"))
        try:
            db.session.add(new_student)
            db.session.commit()
            flash("Student added successfully!", "success")
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error adding student: {str(e)}")
            flash(f"Error adding student: {str(e)}", "error")
        return redirect(url_for("students"))

    return render_template("students.html", students=allstudents, selected_semester=selected_semester, alldepartments=alldepartments, max_year=max_year, students_year=students_year, department=selectedDepartment, current_first_year=current_first_year)

@app.route('/addcourse', methods=['POST'])
def add_course():
    selectedDepartmentName = session.get("selectedDepartment") or request.form.get("selectedDepartment")

    if not selectedDepartmentName:
        flash("No department selected.", "error")
        return redirect(url_for("students"))

    selectedDepartment = Department.query.filter_by(department_name=selectedDepartmentName).first()

    if not selectedDepartment:
        flash("Department not found.", "error")
        return redirect(url_for("students"))

    courseName = request.form.get("courseName")
    if not courseName:
        flash("Course name is required.", "error")
        return redirect(url_for("students"))

    try:
        new_course = Course(course_name=courseName, department=selectedDepartment)
        db.session.add(new_course)
        db.session.commit()
        flash("Course added successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error adding course: {str(e)}", "error")
        return redirect(url_for("students"))

    return redirect(url_for("students"))

@app.route('/update_all_students', methods=['POST'])
def update_all_students():
    if request.method == 'POST':
        student_ids = request.form.getlist('student_ids')
        if not student_ids:
            flash('No student data submitted for update.', 'info')
            return redirect(url_for('students'))
        updated_count = 0
        error_count = 0
        for student_id_str in student_ids:
            try:
                student_id = int(student_id_str)
                student_to_update = Student.query.get(student_id)
                if student_to_update:
                    student_to_update.name = request.form.get(f'name_{student_id}', student_to_update.name).strip()
                    student_to_update.contactNum = request.form.get(f'contactNum_{student_id}', student_to_update.contactNum).strip() or "N/A"
                    student_to_update.contactPerson = request.form.get(f'contactPerson_{student_id}', student_to_update.contactPerson).strip() or "N/A"
                    student_to_update.address = request.form.get(f'address_{student_id}', student_to_update.address).strip() or "N/A"
                    status_value = request.form.get(f'status_{student_id}')
                    if status_value == '1':
                        status = True
                    else:
                        status = False
                    student_to_update.status = status
                    # Handle image upload
                    image_file = request.files.get(f'image_{student_id}')
                    if image_file and image_file.filename:
                        try:
                            filename = secure_filename(image_file.filename)
                            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                            unique_filename = f"{timestamp}_{filename}"
                            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                            image_file.save(file_path)
                            # Optionally, delete the old image
                            if student_to_update.image_path and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(student_to_update.image_path))):
                                try:
                                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(student_to_update.image_path)))
                                except Exception as e:
                                    logging.warning(f"Failed to delete old image {student_to_update.image_path}: {str(e)}")
                            student_to_update.image_path = f"uploads/{unique_filename}"
                        except Exception as e:
                            db.session.rollback()
                            logging.error(f"Error saving image for student ID {student_id}: {str(e)}")
                            flash(f"Error saving image for student ID {student_id}: {str(e)}", "error")
                            error_count += 1
                            continue
                    updated_count += 1
                else:
                    logging.warning(f"Student with ID {student_id} not found during batch update.")
                    error_count += 1
            except ValueError:
                logging.error(f"Invalid student ID format encountered: {student_id_str}")
                error_count += 1
            except Exception as e:
                db.session.rollback()
                logging.error(f"Error updating student ID {student_id_str}: {str(e)}")
                flash(f"Error updating student ID {student_id_str}. Changes for this student were rolled back.", "error")
                error_count += 1
        try:
            if updated_count > 0:
                db.session.commit()
                # flash(f'{updated_count} student record(s) updated successfully!', 'success')
            if error_count > 0:
                flash(f'{error_count} student record(s) could not be updated. Check logs.', 'error')
            if updated_count == 0 and error_count == 0 and student_ids:
                flash('No changes detected or no students found for submitted IDs.', 'info')
        except Exception as e:
            db.session.rollback()
            logging.error(f"Critical error committing batch student updates: {str(e)}")
            flash('A critical error occurred while saving changes. All changes for this batch have been rolled back.', 'error')
        return redirect(url_for('students'))
    return redirect(url_for('students'))

@app.route("/delete_student/<int:student_id>", methods=["DELETE"])
def delete_student(student_id):
    student = Student.query.get(student_id)
    if student:
        try:
            # Delete associated image file if it exists
            if student.image_path and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(student.image_path))):
                try:
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(student.image_path)))
                except Exception as e:
                    logging.warning(f"Failed to delete image {student.image_path}: {str(e)}")
            db.session.delete(student)
            db.session.commit()
            return jsonify({"success": True, "message": "Student deleted successfully."}), 200
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error deleting student ID {student_id}: {str(e)}")
            return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500
    return jsonify({"success": False, "message": "Student not found."}), 404

@app.route("/payables", methods=["GET", "POST"])
def add_payable():
    department = session.get("selectedDepartment") or request.form.get("selectedDepartment")
    selected_semester = session.get("selectedSemester") or request.form.get("selectedSemester")

    if request.method == "POST":
        data = request.form
        payable_name = data["name"]
        amount = float(data["price"])
        category = data["category"]
        payable_department = session.get("selectedDepartment") or request.form.get("selectedDepartment")
        try:
            new_payable = Payable(payable_name=payable_name, amount=amount, category=category, payable_department=payable_department)
            db.session.add(new_payable)
            db.session.commit()
            flash("Payable added successfully!", "success")
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error inserting payable: {e}")
            flash(f"Error adding payable: {str(e)}", "error")
        return redirect(url_for("add_payable"))
    return render_template("Payables.html", department=department, selected_semester=selected_semester)

@app.route("/submit_payables", methods=["POST"])
def submit_payables():
    data = request.get_json()
    try:
        for item in data:
            payable_name = item['payable_name']
            amount = item['amount']
            category = item['category']
            payable_department = session.get("selectedDepartment") or request.form.get("selectedDepartment")
            new_payable = Payable(payable_name=payable_name, amount=amount, category=category, payable_department=payable_department)
            db.session.add(new_payable)
        db.session.commit()
        return jsonify({"message": "Payables submitted successfully!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@app.route("/studentpayable")
def studentpayable():
    department = session.get("selectedDepartment") or request.form.get("selectedDepartment")
    selected_semester = session.get("selectedSemester") or request.form.get("selectedSemester")

    try:
        department = session.get("selectedDepartment") or request.form.get("selectedDepartment") or "default_dept"
        allpayables = Payable.query.filter(Payable.payable_department == department).all()
        students = Student.query.filter(Student.department == department).all()
        students_data = [
            {"id": s.id, "student_number": s.student_number, "name": s.name, "image_path": getattr(s, 'image_path', None)}
            for s in students
        ]
        return render_template("StudentPayable.html", selected_semester=selected_semester, allpayables=allpayables, students=students_data, department=department)
    except Exception as e:
        logging.error(f"Error in studentpayable route: {str(e)}")
        return "Internal Server Error - Check logs", 500

@app.route("/delete_payable/<int:id>", methods=["DELETE"])
def delete_payable(id):
    payable = Payable.query.get(id)
    if payable:
        db.session.delete(payable)
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Payable not found"}), 404

@app.route('/assign_payables', methods=["POST"])
def assign_payables():
    selected_semester = session.get("selectedSemester") or request.form.get("selectedSemester")

    data = request.get_json()
    student_id = data.get("student_id")
    selected = data.get("payables", [])
    student = Student.query.get(student_id)
    if not student:
        return jsonify({"error": "Student not found"}), 404
    existing_payables = {
        sp.payable_id: sp
        for sp in student.student_payables
        if sp.semester == selected_semester
    }

    for item in selected:
        payable_id = item.get("id")
        quantity = item.get("quantity", 1)
        payable = Payable.query.get(payable_id)
        if payable:
            if payable_id in existing_payables:
                existing_sp = existing_payables[payable_id]
                if quantity > existing_sp.quantity:
                    existing_sp.quantity = quantity
            else:
                sp = StudentPayable(student=student, payable=payable, quantity=quantity, semester=selected_semester)
                db.session.add(sp)
    db.session.commit()
    return jsonify({"message": "Payables assigned successfully."})

@app.route("/payment")
def payment():
    department = session.get("selectedDepartment") or request.form.get("selectedDepartment")
    selected_semester = session.get("selectedSemester") or request.form.get("selectedSemester")

    payables = Payable.query.filter(Payable.payable_department == department).all()
    students = Student.query.filter(Student.department == department).all()
    students_data = [
        {"id": s.id, "student_number": s.student_number, "name": s.name}
        for s in students
    ]
    payables_data = []
    for p in payables:
        quantity_map = {
            sp.student.id: sp.quantity
            for sp in p.student_payables
            if sp.semester == selected_semester
        }
        is_paid_map = {
            sp.student.id: sp.is_paid
            for sp in p.student_payables
            if sp.semester == selected_semester
        }
        payables_data.append({
            "id": p.id,
            "payable_name": p.payable_name,
            "amount": p.amount,
            "semester_payment": selected_semester,
            "student_ids": list(quantity_map.keys()),
            "quantities": quantity_map,
            "is_paid": is_paid_map
        })
    return render_template("Payment.html", students=students_data, payables=payables_data, department=department, selected_semester=selected_semester)

@app.route("/update_payable/<int:student_id>", methods=["POST"])
def updatePayable(student_id):
    data = request.get_json()
    student = Student.query.get(student_id)
    paid_payables = data
    try:
        for item in paid_payables:
            name = item.get("payable_name")
            for sp in student.student_payables:
                if name == sp.payable.payable_name:
                    sp.is_paid = True
        db.session.commit()
        return jsonify({"message": "Payment successful."})
    except Exception as e:
        logging.error(f"Error updating payable: {e}")
        return jsonify({"error": str(e)}), 500

def get_remaining_bal(student_id):
    selected_semester = session.get("selectedSemester") or request.form.get("selectedSemester")
    student = Student.query.get(student_id)
    if not student:
        raise ValueError("Student not found")

    total_payables = 0
    for sp in student.student_payables:
        if sp.semester == selected_semester:
            total_payables += sp.payable.amount * sp.quantity

    total_paid = sum(p.amount_paid for p in student.payments if p.semester_payment == selected_semester)

    remaining_balance = max(total_payables - total_paid, 0)
    remaining_balance += get_previous_remaining_bal(student_id, selected_semester)
    return remaining_balance


@app.route("/process_payment", methods=["POST"])
def process_payment():
    semester_payment = session.get("selectedSemester") or request.form.get("selectedSemester")
    data = request.form
    student_id = data.get("student_id")
    amount_paid = float(data.get("payables_to_pay", 0))

    if not student_id or amount_paid <= 0:
        flash("Invalid payment data.", "error")
        return redirect(url_for("payment"))

    student = Student.query.get(student_id)
    if not student:
        flash("Student not found.", "error")
        return redirect(url_for("payment"))

    try:
        remaining_balance = get_remaining_bal(student_id)
    except Exception as e:
        logging.error(f"Error calculating balance for student ID {student_id}: {str(e)}")
        flash("Error getting remaining balance.", "error")
        return redirect(url_for("payment"))

    is_fully_paid = amount_paid >= remaining_balance

    try:
        new_payment = Payment(
            student_id=student_id,
            amount_paid=amount_paid,
            semester_payment=semester_payment,
            is_fully_paid=is_fully_paid
        )
        db.session.add(new_payment)
        db.session.commit()
        flash("Payment recorded successfully!", "success")
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error recording payment for student ID {student_id}: {str(e)}")
        flash(f"Error recording payment: {str(e)}", "error")

    return redirect(url_for("payment"))


@app.route("/get_remaining_balance/<int:student_id>", methods=["GET"])
def get_remaining_balance(student_id):
    selected_semester = session.get("selectedSemester") or request.form.get("selectedSemester")
    student = Student.query.get(student_id)
    if not student:
        raise ValueError("Student not found")

    total_payables = 0
    for sp in student.student_payables:
        if sp.semester == selected_semester:
            total_payables += sp.payable.amount * sp.quantity

    total_paid = sum(p.amount_paid for p in student.payments if p.semester_payment == selected_semester)

    remaining_balance = max(total_payables - total_paid, 0)
    remaining_balance += get_previous_remaining_bal(student_id, selected_semester)
    return jsonify({"remaining_balance": remaining_balance})

def is_Fully_Paid(self):
    total_payables = sum(sp.payable.amount * sp.quantity for sp in self.student_payables)
    total_paid = sum(p.amount_paid for p in self.payments)
    return total_paid >= total_payables

def view_students():
    year = request.args.get('year')
    department = session.get("selectedDepartment") or request.form.get("selectedDepartment")
    if year:
        students = Student.query.filter(Student.department == department, Student.student_number.startswith(year)).order_by(Student.student_number).all()
    else:
        students = Student.query.filter(Student.department == department).order_by(desc(func.substr(Student.student_number, 1, 2)), asc(func.substr(Student.student_number, 4, 2)), asc(func.substr(Student.student_number, 7, 2)) ).all()
    return render_template('report.html', students=students)

def get_previous_remaining_bal(student_id, selected_semester=None):
    if selected_semester is None:
        selected_semester = session.get("selectedSemester") or request.form.get("selectedSemester")

    if selected_semester[-3:] == "2ND":
        previous_semester = selected_semester[:9] + "_1ST"
    else:
        school_year = int(selected_semester[:4])
        previous_school_year = school_year - 1
        previous_semester = f"{previous_school_year}-{school_year}_2ND"

    if int(selected_semester[:4]) < 2020:
        return 0

    student = Student.query.get(student_id)
    if not student:
        raise ValueError("Student not found")

    total_payables = sum(
        sp.payable.amount * sp.quantity
        for sp in student.student_payables
        if sp.semester == previous_semester
    )

    total_paid = sum(
        p.amount_paid
        for p in student.payments
        if p.semester_payment == previous_semester
    )

    remaining_balance = max(total_payables - total_paid, 0)
    previous_balance = get_previous_remaining_bal(student_id, previous_semester)

    return remaining_balance + previous_balance

@app.route("/report", methods=["POST", "GET"])
def report():
    selected_semester = session.get("selectedSemester") or request.form.get("selectedSemester")
    department = session.get("selectedDepartment") or request.form.get("selectedDepartment")
    # categories_list = db.session.query(Payable.category).distinct().all()
    # payable_categories = [c[0] for c in categories_list]
    payable_categories = ["uniform", "module", "penalty", "org", "defense", "others"]
    allstudents = Student.query.filter(Student.department == department).all()
    allpayables = Payable.query.filter().all()
    uniformTax = 0


    alldepartment = Department.query.all()
    for curr_department in alldepartment:
        if curr_department.department_name == department:
            departmentTax = float(curr_department.department_tax)

    for payable in allpayables:
        if payable.category == "uniform":
            uniformTax = float(payable.payable_tax)
            break

    if request.method == "POST":
        data = request.form

        if "tax" in data:
            departmentTax = float(data["tax"])
            for curr_department in alldepartment:
                if curr_department.department_name == department:
                    curr_department.department_tax = float(departmentTax)

        if "unif" in data:
            uniformTax = float(data["unif"])
            for payable in allpayables:
                if payable.category == "uniform":
                    payable.payable_tax = float(uniformTax)

        db.session.commit()

    current_first_year = int(selected_semester[2:4])

    year = request.args.get('year')

    if year == "01":
        students_year = Student.query.filter(Student.department == department,
                                             Student.status == False).order_by(
            Student.student_number).all()
    elif year:
        students_year = Student.query.filter(Student.department == department, Student.status == True, Student.student_number.startswith(year)).order_by(Student.student_number).all()
    else:
        students_year = Student.query.filter(Student.department == department, Student.status == True, Student.student_number.startswith(current_first_year)).order_by(Student.student_number).all()
    department = session.get("selectedDepartment") or request.form.get("selectedDepartment")

    students_year_payables = []

    for students in students_year:
        for sp in students.student_payables:
            if sp.semester == selected_semester:
                if sp.payable.payable_name not in students_year_payables:
                    students_year_payables.append(sp.payable.payable_name)

    payables = Payable.query.filter(Payable.payable_department == department, Payable.payable_name.in_(students_year_payables)).all()
    students = Student.query.filter(Student.department == department).order_by(desc(func.substr(Student.student_number, 1, 2)), asc(func.substr(Student.student_number, 4, 2)), asc(func.substr(Student.student_number, 7, 2)) ).all()
    allQuantity = moduleQuantity = uniformQuantity = uniform = module = penalty = org = defense = others = dept_funds = 0.0
    for student in students:
        for payable in student.student_payables:
            if payable.semester == selected_semester:
                if payable.payable.payable_department == department:
                    if payable.is_paid:
                        allQuantity += payable.quantity
                        # dept_funds += ((payable.payable.amount * payable.quantity)-(payable.quantity * departmentTax))
                        category = payable.payable.category
                        match category:
                            case "uniform":
                                uniform += ((payable.payable.amount * payable.quantity)-(payable.quantity * uniformTax))
                                uniformQuantity += payable.quantity
                                payable.payable_tax = uniformTax
                            case "module":
                                module += ((payable.payable.amount * payable.quantity)-(payable.quantity * departmentTax))
                                moduleQuantity += payable.quantity
                            case "penalty":
                                penalty += (payable.payable.amount * payable.quantity)
                            case "org":
                                org += (payable.payable.amount * payable.quantity)
                            case "defense":
                                defense += (payable.payable.amount * payable.quantity)
                            case "others":
                                others += (payable.payable.amount * payable.quantity)
    dept_funds = (uniform + module + penalty + org + defense + others)
    departmentFunds = dept_funds
    totalModuleTax = float(moduleQuantity * departmentTax)
    totalUniformTax = float(uniformQuantity * uniformTax)
    return render_template("report.html", selected_semester=selected_semester, allpayables=allpayables, allstudents=allstudents, payable_categories=payable_categories, department=department, departmentTax=departmentTax, uniformTax=uniformTax, totalUniformTax=totalUniformTax, totalModuleTax=totalModuleTax, students_year=students_year, current_first_year=current_first_year, students=students, payables=payables, get_previous_remaining_bal=get_previous_remaining_bal, get_remaining_bal=get_remaining_bal, departmentFunds=departmentFunds, uniform=uniform, module=module, penalty=penalty, org=org, defense=defense, others=others)

@app.route("/logout")
def logout():
    return redirect(url_for("login"))

def run_flask():
    app.run(debug=True, use_reloader=False)

def open_main():
    webview.windows[0].maximize()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    thread = Thread(target=run_flask)
    thread.start()
    webview.create_window('Department Payables', 'http://127.0.0.1:5000', fullscreen=False, resizable=False)
    webview.start(open_main)

