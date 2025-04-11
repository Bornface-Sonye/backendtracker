from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse_lazy, reverse
from django.contrib.auth import logout  # Import the logout function
from django.views.generic import DeleteView, ListView, FormView
from django.conf import settings
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from django.utils import timezone
from datetime import timedelta

from django.db import transaction
from django.db import IntegrityError


from .models import (
Student, UnitOffering, Complaint, Course, YearOfStudy, AcademicYear, Semester, Lecturer, LecturerUnit,
PasswordResetToken, Complaint, System_User
)

from .forms import (
SignUpForm, LoginForm, StudentForm, MissingMarkForm
)

from django.contrib import messages
from .utils import generate_unique_complaint_code  # import the utility

import re
from django.core.exceptions import ValidationError
import pandas as pd
import random
import string
from django.contrib import messages


class StudentSelectView(View):
    def get(self, request):
        form = StudentForm()
        return render(request, 'student_reg_no.html', {'form': form})

    def post(self, request):
        form = StudentForm(request.POST)
        if form.is_valid():
            reg_no = form.cleaned_data['registration_no']
            course_code = form.cleaned_data['course']
            year_of_study = form.cleaned_data['year_of_study']
            academic_year = form.cleaned_data['academic_year']
            semester = form.cleaned_data['semester']

            try:
                student = Student.objects.get(registration_no=reg_no, course__course_code=course_code)
            except Student.DoesNotExist:
                form.add_error('registration_no', 'Student not found.')
                return render(request, 'student_reg_no.html', {'form': form})

            course = Course.objects.get(course_code=course_code)

            request.session['student_data'] = {
                'reg_no': reg_no,
                'course': course.course_code,
                'year_of_study': year_of_study.study_year,
                'academic_year': academic_year.academic_year,
                'semester_id': semester.semester_id
            }

            return redirect('post-complaint')

        return render(request, 'student_reg_no.html', {'form': form})


class MissingMarkSelectView(View):
    def get_student_unit_queryset(self, student_data):
        course = Course.objects.get(course_code=student_data['course'])
        year_of_study = YearOfStudy.objects.get(study_year=student_data['year_of_study'])
        academic_year = AcademicYear.objects.get(academic_year=student_data['academic_year'])
        semester = Semester.objects.get(semester_id=student_data['semester_id'])

        return UnitOffering.objects.filter(
            course=course,
            year_of_study=year_of_study,
            academic_year=academic_year,
            semester=semester
        )

    def get(self, request):
        student_data = request.session.get('student_data')
        if not student_data:
            return redirect('student')

        units = self.get_student_unit_queryset(student_data)

        form = MissingMarkForm()
        form.fields['unit'].queryset = units

        return render(request, 'post_complaint.html', {'form': form})

    def post(self, request):
        student_data = request.session.get('student_data')
        if not student_data:
            return redirect('student')

        units = self.get_student_unit_queryset(student_data)

        form = MissingMarkForm(request.POST)
        form.fields['unit'].queryset = units

        if form.is_valid():
            unit = form.cleaned_data['unit']
            missing_types = form.cleaned_data['missing_mark_type']
            student = Student.objects.get(registration_no=student_data['reg_no'])

            # Check if complaint already exists
            if Complaint.objects.filter(student=student, unit_offering=unit).exists():
                messages.warning(request, 'You have already submitted a complaint for this unit.')
                return render(request, 'post_complaint.html', {'form': form})

            # Determine missing type
            missing_type = 'BOTH' if 'CAT' in missing_types and 'EXAM' in missing_types else missing_types[0]

            # Generate complaint code
            complaint_code = generate_unique_complaint_code()

            # Save the complaint
            Complaint.objects.create(
                complaint_code=complaint_code,
                student=student,
                unit_offering=unit,
                missing_type=missing_type
            )

            messages.success(request, 'Your complaint has been successfully submitted.')
            return render(request, 'post_complaint.html', {'form': form})

        return render(request, 'post_complaint.html', {'form': form})
    

class SignUpView(View):
    template_name = 'signup.html'

    def get(self, request):
        form = SignUpForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = SignUpForm(request.POST)

        if form.is_valid():
            username = form.cleaned_data['username']
            password_hash = form.cleaned_data['password_hash']

            # Check if username already exists in System_User model
            if System_User.objects.filter(username=username).exists():
                form.add_error('username', "This username has already been used in the system!")
                return render(request, self.template_name, {'form': form})
            if self.is_lecturer_username(username):
                # Check if the lecturer exists in the Lecturer model
                if not Lecturer.objects.filter(username=username).exists():
                    form.add_error('username', "This lecturer email does not exist.")
                    return render(request, self.template_name, {'form': form})
            else:
                form.add_error('username', "Invalid Username format. Please enter a valid Lecturer Username.")
                return render(request, self.template_name, {'form': form})

            # Create the account if all checks pass
            new_account = form.save(commit=False)
            new_account.set_password(password_hash)
            new_account.save()
            return redirect('login')
        else:
            # If the form is not valid, render the template with the form and errors
            return render(request, self.template_name, {'form': form})

    def is_lecturer_username(self, username):
        # Check if the username is in the lecturer email format
        return bool(re.match(r'^[a-zA-Z0-9]{1,15}@mmust\.ac\.ke$', username))



class LoginView(View):
    template_name = 'login.html'

    def get(self, request):
        form = LoginForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            if self.is_lecturer_username(username):
                # Check if the username exists in the System_User model
                user = System_User.objects.filter(username=username).first()
                if user and user.check_password(password):
                    # Check if the user exists in the Lecturer model
                    lecturer = Lecturer.objects.filter(username=username).first()
                    if lecturer is not None:
                        role = lecturer.role
                        request.session['username'] = user.username  # Store username in session
                        if role == "Member":
                            return redirect(reverse('lecturer-dashboard'))
                        elif role == "Exam Officer":
                            return redirect(reverse('exam-dashboard'))
                        elif role == "COD":
                            return redirect(reverse('cod-dashboard'))
                    else:
                        # Username does not exist in Lecturer model
                        form.add_error('username', "Wrong Username or Password.")
                else:
                    # Authentication failed for lecturer
                    form.add_error('username', "Wrong Username or Password.")

        return render(request, self.template_name, {'form': form})

    def is_lecturer_username(self, username):
        # Check if the username is in the lecturer email format
        return bool(re.match(r'^[a-zA-Z0-9]{1,15}@mmust\.ac\.ke$', username))

class LogoutView(View):
    def get(self, request, *args, **kwargs):
        logout(request)  # Use logout directly
        return redirect('login')  # Redirect to the login page or another appropriate page

class Lecturer_DashboardView(View):
    def get(self, request):
        # Retrieve username from session
        username = request.session.get('username')
        if not username:
            return redirect('login')  # Redirect to login if username is missing

        # Get logged-in lecturer details
        lecturer = Lecturer.objects.filter(username=username).first()
        last_name = lecturer.last_name  # Add last name to context
        user = System_User.objects.get(username=username)
        if not lecturer:
            return redirect('login')  # Redirect if no matching lecturer found

        department_name = lecturer.dep_code.dep_name

        # Total students taking courses related to the lecturer's department
        total_students = Student.objects.filter(
            course_code__dep_code=lecturer.dep_code
        ).count()

        # Total lecturers within the same department
        total_lecturers_in_department = Lecturer.objects.filter(
            dep_code=lecturer.dep_code
        ).count()

        # Total units related to the lecturer from LecturerUnit model
        total_units_for_lecturer = LecturerUnit.objects.filter(
            lec_no=lecturer.lec_no
        ).count()

        # Filter complaints related to lecturer's unit codes, academic year, and course codes
        lecturer_unit_codes = LecturerUnit.objects.filter(
            lec_no=lecturer.lec_no
        ).values_list('unit_code', flat=True)

        related_complaints_count = Complaint.objects.filter(
            unit_code__in=lecturer_unit_codes,
            academic_year__in=LecturerUnit.objects.filter(lec_no=lecturer).values_list('academic_year', flat=True),
            reg_no__course_code__in=LecturerUnit.objects.filter(lec_no=lecturer).values_list('course_code', flat=True)
        ).count()


        # Get all LecturerUnit instances for the lecturer
        units = LecturerUnit.objects.filter(lec_no=lecturer.lec_no)


        # Fetch all courses in the lecturer's department
        courses = Course.objects.filter(dep_code=lecturer.dep_code)

        # Pass calculated counts, units, and courses to the template
        context = {
            'total_students': total_students,
            'total_lecturers_in_department': total_lecturers_in_department,
            'total_units_for_lecturer': total_units_for_lecturer,
            'related_complaints_count': related_complaints_count,
            'last_name': last_name,
            'user': user,
            'units': units,
            'courses': courses,
            'department_name': department_name,
        }

        return render(request, 'lecturer_dashboard.html', context)

class Exam_DashboardView(View):
    def get(self, request):
        # Retrieve username from session
        username = request.session.get('username')
        if not username:
            return redirect('login')  # Redirect to login if username is missing

        # Get logged-in lecturer details
        lecturer = Lecturer.objects.filter(username=username).first()
        last_name = lecturer.last_name  # Add last name to context
        user = System_User.objects.get(username=username)
        if not lecturer:
            return redirect('login')  # Redirect if no matching lecturer found

        department_name = lecturer.dep_code.dep_name

        # Total students taking courses related to the lecturer's department
        total_students = Student.objects.filter(
            course_code__dep_code=lecturer.dep_code
        ).count()

        # Total lecturers within the same department
        total_lecturers_in_department = Lecturer.objects.filter(
            dep_code=lecturer.dep_code
        ).count()

        # Total units related to the lecturer from LecturerUnit model
        total_units_for_lecturer = LecturerUnit.objects.filter(
            lec_no=lecturer.lec_no
        ).count()

        # Filter complaints related to lecturer's unit codes, academic year, and course codes
        lecturer_unit_codes = LecturerUnit.objects.filter(
            lec_no=lecturer.lec_no
        ).values_list('unit_code', flat=True)

        related_complaints_count = Complaint.objects.filter(
            unit_code__in=lecturer_unit_codes,
            academic_year__in=LecturerUnit.objects.filter(lec_no=lecturer).values_list('academic_year', flat=True),
            reg_no__course_code__in=LecturerUnit.objects.filter(lec_no=lecturer).values_list('course_code', flat=True)
        ).count()

        # Get all LecturerUnit instances for the lecturer
        units = LecturerUnit.objects.filter(lec_no=lecturer.lec_no)

        # Fetch all courses in the lecturer's department
        courses = Course.objects.filter(dep_code=lecturer.dep_code)

        # Pass calculated counts, units, and courses to the template
        context = {
            'total_students': total_students,
            'total_lecturers_in_department': total_lecturers_in_department,
            'total_units_for_lecturer': total_units_for_lecturer,
            'related_complaints_count': related_complaints_count,
            'last_name': last_name,
            'user': user,
            'units': units,
            'courses': courses,
            'department_name': department_name,
        }

        return render(request, 'exam_dashboard.html', context)

class COD_DashboardView(View):
    def get(self, request):
        # Retrieve username from session
        username = request.session.get('username')
        if not username:
            return redirect('login')  # Redirect to login if username is missing

        # Get logged-in lecturer details
        lecturer = Lecturer.objects.filter(username=username).first()
        last_name = lecturer.last_name  # Add last name to context
        user = System_User.objects.get(username=username)
        if not lecturer:
            return redirect('login')  # Redirect if no matching lecturer found

        department_name = lecturer.dep_code.dep_name

        # Total students taking courses related to the lecturer's department
        total_students = Student.objects.filter(
            course_code__dep_code=lecturer.dep_code
        ).count()

        # Total lecturers within the same department
        total_lecturers_in_department = Lecturer.objects.filter(
            dep_code=lecturer.dep_code
        ).count()

        # Total units related to the lecturer from LecturerUnit model
        total_units_for_lecturer = LecturerUnit.objects.filter(
            lec_no=lecturer.lec_no
        ).count()

        # Filter complaints related to lecturer's unit codes, academic year, and course codes
        lecturer_unit_codes = LecturerUnit.objects.filter(
            lec_no=lecturer.lec_no
        ).values_list('unit_code', flat=True)

        related_complaints_count = Complaint.objects.filter(
            unit_code__in=lecturer_unit_codes,
            academic_year__in=LecturerUnit.objects.filter(lec_no=lecturer).values_list('academic_year', flat=True),
            reg_no__course_code__in=LecturerUnit.objects.filter(lec_no=lecturer).values_list('course_code', flat=True)
        ).count()

        # Get all LecturerUnit instances for the lecturer
        units = LecturerUnit.objects.filter(lec_no=lecturer.lec_no)

        # Fetch all courses in the lecturer's department
        courses = Course.objects.filter(dep_code=lecturer.dep_code)

        # Pass calculated counts, units, and courses to the template
        context = {
            'total_students': total_students,
            'total_lecturers_in_department': total_lecturers_in_department,
            'total_units_for_lecturer': total_units_for_lecturer,
            'related_complaints_count': related_complaints_count,
            'last_name': last_name,
            'user': user,
            'units': units,
            'courses': courses,
            'department_name': department_name,
        }

        return render(request, 'cod_dashboard.html', context)