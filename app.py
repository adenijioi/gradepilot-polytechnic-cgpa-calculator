import os, uuid
from decimal import Decimal, InvalidOperation
from flask import Flask, abort, flash, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
SEMESTERS = ("Semester 1", "Semester 2", "Semester 3", "Semester 4")
MAX_COURSES = 15

class Calculation(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_name = db.Column(db.String(120), nullable=False)
    matric_number = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    courses = db.relationship("Course", backref="calculation", cascade="all, delete-orphan")

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    calculation_id = db.Column(db.String(36), db.ForeignKey("calculation.id"), nullable=False, index=True)
    semester = db.Column(db.Integer, nullable=False)
    course_code = db.Column(db.String(20), nullable=False)
    course_unit = db.Column(db.Integer, nullable=False)
    score = db.Column(db.Numeric(5,2), nullable=False)

def grade_for(score):
    for minimum, grade, point in ((75,"A","4.00"),(70,"AB","3.50"),(65,"B","3.25"),(60,"BC","3.00"),(55,"C","2.75"),(50,"CD","2.50"),(45,"D","2.25"),(40,"E","2.00")):
        if score >= minimum: return grade, Decimal(point)
    return "F", Decimal("0.00")

def classification(cgpa):
    if cgpa >= Decimal("3.50"): return "Distinction"
    if cgpa >= Decimal("3.00"): return "Upper Credit"
    if cgpa >= Decimal("2.50"): return "Lower Credit"
    if cgpa >= Decimal("2.00"): return "Pass"
    return "Fail"

def compile_results(courses):
    semesters, total_units, total_qp = [], 0, Decimal("0")
    for number, name in enumerate(SEMESTERS, 1):
        rows, units, qp = [], 0, Decimal("0")
        for c in sorted((x for x in courses if x.semester == number), key=lambda x: x.id or 0):
            score = Decimal(c.score); grade, point = grade_for(score); quality = point*c.course_unit
            units += c.course_unit; qp += quality
            rows.append(dict(code=c.course_code, unit=c.course_unit, score=score, grade=grade, grade_point=point, quality_point=quality))
        semesters.append(dict(number=number,name=name,courses=rows,units=units,quality_points=qp,gpa=qp/units if units else Decimal("0")))
        total_units += units; total_qp += qp
    cgpa = total_qp/total_units if total_units else Decimal("0")
    return dict(semesters=semesters,total_units=total_units,total_quality_points=total_qp,cgpa=cgpa,classification=classification(cgpa))

def parse_courses(form):
    courses, errors = [], []
    for semester in range(1,5):
        codes, units, scores = (form.getlist(f"{key}_{semester}[]") for key in ("course_code","course_unit","score"))
        if len(codes) > MAX_COURSES: errors.append(f"Semester {semester} cannot contain more than 15 courses."); continue
        seen=set()
        for row,(code,unit_text,score_text) in enumerate(zip(codes,units,scores),1):
            code,unit_text,score_text=code.strip().upper(),unit_text.strip(),score_text.strip()
            if not any((code,unit_text,score_text)): continue
            if not all((code,unit_text,score_text)): errors.append(f"Complete every field in Semester {semester}, row {row}."); continue
            if code in seen: errors.append(f"{code} is entered more than once in Semester {semester}.")
            seen.add(code)
            try:
                unit=int(unit_text); score=Decimal(score_text)
                if not 1<=unit<=10 or not Decimal("0")<=score<=Decimal("100"): raise ValueError
            except (ValueError,InvalidOperation): errors.append(f"Semester {semester}, row {row} has an invalid unit or score."); continue
            courses.append(Course(semester=semester,course_code=code[:20],course_unit=unit,score=score))
    if not courses: errors.append("Enter at least one complete course before calculating.")
    return courses,errors

def create_app(test_config=None):
    app=Flask(__name__)
    db_url=os.getenv("DATABASE_URL","sqlite:///cgpa.db")
    if db_url.startswith("postgres://"): db_url=db_url.replace("postgres://","postgresql+psycopg://",1)
    elif db_url.startswith("postgresql://"): db_url=db_url.replace("postgresql://","postgresql+psycopg://",1)
    app.config.update(SECRET_KEY=os.getenv("SECRET_KEY","dev-change-me"),SQLALCHEMY_DATABASE_URI=db_url,SQLALCHEMY_TRACK_MODIFICATIONS=False)
    if test_config: app.config.update(test_config)
    db.init_app(app)
    @app.after_request
    def headers(response):
        response.headers.update({"X-Content-Type-Options":"nosniff","X-Frame-Options":"SAMEORIGIN","Referrer-Policy":"strict-origin-when-cross-origin"}); return response
    @app.get("/")
    def index(): return render_template("index.html",semesters=SEMESTERS,max_courses=MAX_COURSES)
    @app.post("/calculate")
    def calculate():
        name=request.form.get("student_name","").strip(); matric=request.form.get("matric_number","").strip(); courses,errors=parse_courses(request.form)
        if not name: errors.insert(0,"Student name is required.")
        if errors:
            for error in errors: flash(error,"danger")
            return redirect(url_for("index"))
        calculation=Calculation(student_name=name[:120],matric_number=matric[:50] or None,courses=courses); db.session.add(calculation); db.session.commit()
        return redirect(url_for("result",calculation_id=calculation.id))
    @app.get("/result/<calculation_id>")
    def result(calculation_id):
        try: uuid.UUID(calculation_id)
        except ValueError: abort(404)
        item=db.session.get(Calculation,calculation_id)
        if not item: abort(404)
        return render_template("result.html",calculation=item,results=compile_results(item.courses))
    @app.get("/health")
    def health(): return {"status":"ok"}
    with app.app_context(): db.create_all()
    return app

app=create_app()
if __name__=="__main__": app.run(debug=True)
