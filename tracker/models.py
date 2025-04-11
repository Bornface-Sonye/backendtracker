from django.db import models
from datetime import date
from django.utils import timezone
import random
import string
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password, check_password
from .validators import validate_reg_no, validate_kenyan_phone_number
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError

class School(models.Model):
    school_code = models.CharField(primary_key=True, unique=True, max_length=20, help_text="Please Enter School Code")
    school_name = models.CharField(max_length=200, help_text="Please Enter School Name")
    
    def __str__(self):
        return f"{self.school_code}"

class Department(models.Model):
    department_code = models.CharField(primary_key=True, unique=True, max_length=20, help_text="Please Enter Department Code")
    department_name = models.CharField(max_length=200, help_text="Please Enter Department Name")
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.department_code}"

class Program(models.Model):
    program_code = models.CharField(max_length=10, primary_key=True, help_text="Please Enter Program Code")
    program_name = models.CharField(max_length=255, help_text="Please Enter Program Name")
    level = models.CharField(max_length=50, choices=[
        ('Certificate', 'Certificate'), 
        ('Diploma', 'Diploma'), 
        ('Degree', 'Degree'), 
        ('Masters', 'Masters'), 
        ('PhD', 'PhD')
    ])
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.program_code}"

class Course(models.Model):
    course_code = models.CharField(primary_key=True, unique=True, max_length=20, help_text="Please Enter Course Code")
    course_name = models.CharField(max_length=200, help_text="Please Enter Course Name")
    program = models.ForeignKey(Program, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.course_code}"

class AcademicYear(models.Model):
    year_id = models.AutoField(primary_key=True)
    academic_year = models.CharField(max_length=200, help_text="Please Enter Academic Year")  # e.g. "2023/2024"
    
    def __str__(self):
        return f"{self.academic_year}"

class Semester(models.Model):
    semester_id = models.AutoField(primary_key=True)
    semester_number = models.PositiveSmallIntegerField(choices=[
        (1, 'Semester 1'), 
        (2, 'Semester 2'), 
        (3, 'Semester 3')
    ])
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.semester_number}"

class YearOfStudy(models.Model):
    study_year = models.PositiveSmallIntegerField(primary_key=True)  # e.g. 1 to 5
    
    def __str__(self):
        return f"{self.study_year}"
    
class Unit(models.Model):
    unit_code = models.CharField(primary_key=True, unique=True, max_length=20, help_text="Please Enter Unit Code")
    unit_name = models.CharField(max_length=200, help_text="Please Enter Unit Name")
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.unit_code}"

class Lecturer(models.Model):
    employee_no = models.CharField(max_length=20, primary_key=True, help_text="Please Enter Lecturer Number")
    email_address = models.EmailField(max_length=200, help_text="Please Enter Lecturer Email Address")
    username = models.EmailField(unique=True, max_length=200, help_text="Enter a valid Username")
    first_name = models.CharField(max_length=200, help_text="Please Enter Student First Name")
    last_name = models.CharField(max_length=200, help_text="Please Enter Student Last Name")
    phone_number = models.CharField(max_length=13, validators=[validate_kenyan_phone_number], help_text="Enter phone number in the format 0798073204 or +254798073404")
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    role = models.CharField(max_length=50, choices=[
        ('Member', 'Member'),
        ('Exam Officer', 'Exam Officer'),
        ('COD', 'COD')
    ])
    
    def __str__(self):
        return f"{self.employee_no}"
    
class LecturerUnit(models.Model):
    unit_code = models.ForeignKey(Unit, on_delete=models.CASCADE)
    employee_no = models.ForeignKey(Lecturer, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    course_code = models.ForeignKey(Course, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.employee_no}"

class Student(models.Model):
    reg_no = models.CharField(primary_key=True, unique=True, max_length=200, validators=[validate_reg_no], help_text="Please Enter Student Registration Number")
    username = models.CharField(unique=True, max_length=200, help_text="Enter a valid Username")
    first_name = models.CharField(max_length=200, help_text="Please Enter Student First Name")
    last_name = models.CharField(max_length=200, help_text="Please Enter Student Last Name")
    email_address = models.EmailField(max_length=200, help_text="Please Enter Student Email Address")
    phone_number = models.CharField(max_length=13, validators=[validate_kenyan_phone_number], help_text="Enter phone number in the format 0798073204 or +254798073404")
    program = models.ForeignKey(Program, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.reg_no}"

class UnitOffering(models.Model):
    offering_id = models.AutoField(primary_key=True)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE)
    year_of_study = models.ForeignKey(YearOfStudy, on_delete=models.CASCADE)
    lecturer = models.ForeignKey(Lecturer, null=True, blank=True, on_delete=models.SET_NULL)
    
    def __str__(self):
        return f"{self.unit} - {self.course} - {self.academic_year}"



class NominalRoll(models.Model):
    unit_code = models.ForeignKey(Unit, on_delete=models.CASCADE)
    reg_no = models.ForeignKey(Student, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['unit_code', 'reg_no', 'academic_year'],
                name='unique_nominal_roll_per_unit_student_year'
            )
        ]

    def __str__(self):
        return f"{self.reg_no} - {self.unit_code} - {self.academic_year}"

    def clean(self):
        # Additional custom validation can be added here if needed
        if not self.unit_code or not self.reg_no or not self.academic_year:
            raise ValidationError("Unit code, student registration number, and academic year must be provided.")

    def save(self, *args, **kwargs):
        # Call clean method to perform validations before saving
        self.clean()
        super().save(*args, **kwargs)

class Result(models.Model):
    unit_code = models.ForeignKey(Unit, on_delete=models.CASCADE)
    reg_no = models.ForeignKey(Student, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    cat = models.IntegerField(
        null=True, 
        blank=True, 
        validators=[MinValueValidator(0), MaxValueValidator(30)]
    )
    exam = models.IntegerField(
        null=True, 
        blank=True, 
        validators=[MinValueValidator(0), MaxValueValidator(70)]
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['unit_code', 'reg_no', 'academic_year'],
                name='unique_result_per_unit_student_year'
            )
        ]

    @property
    def total(self):
        return (self.cat or 0) + (self.exam or 0)

    def __str__(self):
        return f"{self.reg_no} - {self.unit_code} - {self.academic_year}"

    def clean(self):
        if not self.unit_code or not self.reg_no or not self.academic_year or not self.cat or not self.exam:
            raise ValidationError("Unit code, student registration number, cat, exam, and academic year must be provided.")
        # Custom validation to ensure cat and exam fields are within range
        if self.cat and not (0 <= self.cat <= 30):
            raise ValidationError({'cat': 'CAT marks should be between 0 and 30.'})
        if self.exam and not (0 <= self.exam <= 70):
            raise ValidationError({'exam': 'Exam marks should be between 0 and 70.'})

    def save(self, *args, **kwargs):
        # Call clean method to perform validations before saving
        self.clean()
        super().save(*args, **kwargs)
        
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
    resolved = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.complaint_code} - {self.student} - {self.missing_type}"
        
    
class Response(models.Model):
    complaint = models.OneToOneField(Complaint, on_delete=models.CASCADE, primary_key=True)
    cat_mark = models.IntegerField(null=True, blank=True)  # 0-30
    exam_mark = models.IntegerField(null=True, blank=True)  # 0-70
    response_date = models.DateTimeField(auto_now_add=True)
    comment_by_cod = models.TextField(null=True, blank=True)
    approved_by_cod = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.complaint} - {self.comment_by_cod} - {self.approved_by_cod}"

class ArchivedComplaint(models.Model):
    complaint_code = models.CharField(
        max_length=100,
        primary_key=True,
        unique=True,
        help_text="Please Enter Complaint Code"
    )
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    unit_offering = models.ForeignKey(UnitOffering, on_delete=models.CASCADE)
    resolved_by = models.ForeignKey(Lecturer, on_delete=models.SET_NULL, null=True)
    deleted_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.complaint} - {self.resolved_by} - {self.deleted_at}"
    
class ArchivedResponse(models.Model):
    archivedcomplaint = models.OneToOneField(ArchivedComplaint, on_delete=models.CASCADE, primary_key=True)
    cat_mark = models.IntegerField(null=True, blank=True)  # 0-30
    exam_mark = models.IntegerField(null=True, blank=True)  # 0-70
    response_date = models.DateTimeField(auto_now_add=True)
    comment_by_cod = models.TextField(null=True, blank=True)
    approved_by_cod = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.complaint} - {self.comment_by_cod} - {self.approved_by_cod}"

class System_User(models.Model):
    username = models.CharField(primary_key=True, unique=True, max_length=50, help_text="Enter a valid Username")
    password_hash = models.CharField(max_length=128, help_text="Enter a valid password")  # Store hashed password

    def set_password(self, raw_password):
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password_hash)

    def clean(self):
        # Custom validation for password field
        if len(self.password_hash) < 8:
            raise ValidationError("Password must be at least 8 characters long.")

    def __str__(self):
        return self.username   

class PasswordResetToken(models.Model):
    username = models.ForeignKey(System_User, on_delete=models.CASCADE)
    token = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Token for {self.username}"

    def is_expired(self):
        expiration_time = self.created_at + timedelta(minutes=5)
        return timezone.now() > expiration_time