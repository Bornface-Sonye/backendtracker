# complaints/admin.py
from django.contrib import admin
from .models import (
    School, Department, Program, Course, AcademicYear, Semester, YearOfStudy, Unit, Lecturer, Student,
    UnitOffering, Complaint, Response, ArchivedComplaint
)

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('school_code', 'school_name')
    search_fields = ('school_code', 'school_name')

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('department_code', 'department_name', 'school')
    list_filter = ('school',)
    search_fields = ('department_code', 'department_name')

@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ('program_code', 'program_name', 'level', 'department')
    list_filter = ('level', 'department')
    search_fields = ('program_code', 'program_name')

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('course_code', 'course_name', 'program')
    list_filter = ('program',)
    search_fields = ('course_code', 'course_name')

@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ('academic_year',)
    search_fields = ('academic_year',)

@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ('semester_id', 'semester_number', 'academic_year')
    list_filter = ('academic_year',)
    search_fields = ('semester_number',)

@admin.register(YearOfStudy)
class YearOfStudyAdmin(admin.ModelAdmin):
    list_display = ('study_year',)
    search_fields = ('study_year',)

@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ('unit_code', 'unit_name', 'department')
    list_filter = ('department',)
    search_fields = ('unit_code', 'unit_name')

@admin.register(Lecturer)
class LecturerAdmin(admin.ModelAdmin):
    list_display = ('employee_no', 'phone_number', 'role')
    list_filter = ('role',)
    search_fields = ('employee_no', 'phone_number', 'role')

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('registration_no', 'program', 'course')
    list_filter = ('program', 'course')
    search_fields = ('registration_no',)

@admin.register(UnitOffering)
class UnitOfferingAdmin(admin.ModelAdmin):
    list_display = ('offering_id', 'unit', 'course', 'academic_year', 'semester', 'year_of_study', 'lecturer')
    list_filter = ('unit', 'course', 'academic_year', 'semester', 'year_of_study')
    search_fields = ('offering_id',)

@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ('complaint_code', 'student', 'unit_offering', 'missing_type', 'submitted_at')
    list_filter = ('unit_offering', 'student', 'missing_type')
    search_fields = ('complaint_code', 'student__registration_no', 'unit_offering__unit_code')

@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = ('complaint', 'cat_mark', 'exam_mark', 'response_date', 'comment_by_cod', 'approved_by_cod')
    list_filter = ('complaint',)
    search_fields = ('complaint__complaint_id',)

@admin.register(ArchivedComplaint)
class ArchivedComplaintAdmin(admin.ModelAdmin):
    list_display = ('complaint', 'resolved_by', 'deleted_at')
    list_filter = ('resolved_by',)
    search_fields = ('complaint__complaint_id',)
