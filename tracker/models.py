from django.db import models

class School(models.Model):
    school_code = models.CharField(max_length=10, primary_key=True)
    school_name = models.CharField(max_length=255)

class Department(models.Model):
    department_code = models.CharField(max_length=10, primary_key=True)
    department_name = models.CharField(max_length=255)
    school = models.ForeignKey(School, on_delete=models.CASCADE)

class Program(models.Model):
    program_code = models.CharField(max_length=10, primary_key=True)
    program_name = models.CharField(max_length=255)
    level = models.CharField(max_length=50, choices=[
        ('Certificate', 'Certificate'), 
        ('Diploma', 'Diploma'), 
        ('Degree', 'Degree'), 
        ('Masters', 'Masters'), 
        ('PhD', 'PhD')
    ])
    department = models.ForeignKey(Department, on_delete=models.CASCADE)

class Course(models.Model):
    course_code = models.CharField(max_length=10, primary_key=True)
    course_name = models.CharField(max_length=255)
    program = models.ForeignKey(Program, on_delete=models.CASCADE)

class AcademicYear(models.Model):
    academic_year = models.CharField(max_length=20, primary_key=True)  # e.g. "2023/2024"

class Semester(models.Model):
    semester_id = models.AutoField(primary_key=True)
    semester_number = models.PositiveSmallIntegerField(choices=[
        (1, 'Semester 1'), 
        (2, 'Semester 2'), 
        (3, 'Semester 3')
    ])
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)

class YearOfStudy(models.Model):
    study_year = models.PositiveSmallIntegerField(primary_key=True)  # e.g. 1 to 5

class Unit(models.Model):
    unit_code = models.CharField(max_length=20, primary_key=True)
    unit_name = models.CharField(max_length=255)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    courses = models.ManyToManyField(Course)

class Lecturer(models.Model):
    employee_no = models.CharField(max_length=20, primary_key=True)
    phone_number = models.CharField(max_length=20)
    departments = models.ManyToManyField(Department)
    role = models.CharField(max_length=50, choices=[
        ('Member', 'Member'),
        ('Exam Officer', 'Exam Officer'),
        ('COD', 'COD')
    ])

class Student(models.Model):
    registration_no = models.CharField(max_length=50, primary_key=True)
    program = models.ForeignKey(Program, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)

class UnitOffering(models.Model):
    offering_id = models.AutoField(primary_key=True)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE)
    year_of_study = models.ForeignKey(YearOfStudy, on_delete=models.CASCADE)
    lecturer = models.ForeignKey(Lecturer, null=True, blank=True, on_delete=models.SET_NULL)

class Complaint(models.Model):
    complaint_code = models.CharField(
        max_length=100,
        primary_key=True,
        unique=True,
        help_text="Please Enter Complaint Code"
    )
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    unit_offering = models.ForeignKey(UnitOffering, on_delete=models.CASCADE)
    missing_type = models.CharField(max_length=10, choices=[
        ('CAT', 'CAT'), 
        ('EXAM', 'EXAM'), 
        ('BOTH', 'Both')
    ])
    submitted_at = models.DateTimeField(auto_now_add=True)
    assigned_lecturer = models.ForeignKey(
        Lecturer, null=True, blank=True, 
        on_delete=models.SET_NULL, related_name='assigned_complaints'
    )
    forwarded_to_exam_officer = models.BooleanField(default=False)

class Response(models.Model):
    complaint = models.OneToOneField(Complaint, on_delete=models.CASCADE, primary_key=True)
    cat_mark = models.IntegerField(null=True, blank=True)  # 0-30
    exam_mark = models.IntegerField(null=True, blank=True)  # 0-70
    response_date = models.DateTimeField(auto_now_add=True)
    comment_by_cod = models.TextField(null=True, blank=True)
    approved_by_cod = models.BooleanField(default=False)

class ArchivedComplaint(models.Model):
    complaint = models.OneToOneField(Complaint, on_delete=models.CASCADE, primary_key=True)
    resolved_by = models.ForeignKey(Lecturer, on_delete=models.SET_NULL, null=True)
    deleted_at = models.DateTimeField(auto_now_add=True)
