from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.urls import reverse_lazy, reverse
from django.contrib.auth import logout  # Import the logout function
from django.views.generic import DeleteView, ListView, FormView, DetailView
from django.conf import settings
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from django.utils import timezone
from datetime import timedelta

from django.db import transaction
from django.http import JsonResponse
from django.db import IntegrityError
from django.contrib.auth.mixins import LoginRequiredMixin

from django.http import Http404

import re
from django.core.exceptions import ValidationError
import pandas as pd
import random
import string

from django.contrib import messages
from .utils import generate_unique_complaint_code

from .models import (
Student, UnitOffering, Complaint, Course, YearOfStudy, AcademicYear, Semester, Lecturer, LecturerUnit,
PasswordResetToken, NominalRoll, Result, Response, Unit, Lecturer, System_User, Department
)

from .forms import (
SignUpForm, LoginForm, StudentForm, MissingMarkForm, UploadFileForm, ResetForm, PasswordResetForm,
AssignLecturerForm, ResponseForm, CODCommentForm
)


class StudentSelectView(View):
    def get(self, request):
        form = StudentForm()
        return render(request, 'student_reg_no.html', {'form': form})

    def post(self, request):
        form = StudentForm(request.POST)
        if form.is_valid():
            reg_no = form.cleaned_data['reg_no']
            course_code = form.cleaned_data['course']
            year_of_study = form.cleaned_data['year_of_study']
            academic_year = form.cleaned_data['academic_year']
            semester = form.cleaned_data['semester']

            try:
                student = Student.objects.get(reg_no=reg_no, course__course_code=course_code)
            except Student.DoesNotExist:
                form.add_error('reg_no', 'Student not found.')
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
            student = Student.objects.get(reg_no=student_data['reg_no'])

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

            if System_User.objects.filter(username=username).exists():
                form.add_error('username', "This username has already been used in the system!")
                return render(request, self.template_name, {'form': form})

            if not self.is_lecturer_username(username) or not Lecturer.objects.filter(username=username).exists():
                form.add_error('username', "Invalid or non-existent lecturer email.")
                return render(request, self.template_name, {'form': form})

            new_account = form.save(commit=False)
            new_account.set_password(password_hash)
            new_account.save()
            return redirect('login')

        return render(request, self.template_name, {'form': form})

    def is_lecturer_username(self, username):
        return bool(re.match(r'^[a-zA-Z0-9]{1,15}@mmust\.ac\.ke$', username))

class LoginView(View):
    template_name = 'login.html'

    def get(self, request):
        return render(request, self.template_name, {'form': LoginForm()})

    def post(self, request):
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            if self.is_lecturer_username(username):
                user = System_User.objects.filter(username=username).first()
                if user and user.check_password(password):
                    lecturer = Lecturer.objects.filter(username=username).first()
                    if lecturer:
                        request.session['username'] = user.username
                        request.session['role'] = lecturer.role
                        request.session['employee_no'] = lecturer.employee_no
                        request.session['department_code'] = str(lecturer.department.department_code)

                        if lecturer.role == "Member":
                            return redirect('lecturer-dashboard')
                        elif lecturer.role == "Exam Officer":
                            return redirect('exam-dashboard')
                        elif lecturer.role == "COD":
                            return redirect('cod-dashboard')

            form.add_error('username', "Wrong Username or Password.")
        return render(request, self.template_name, {'form': form})

    def is_lecturer_username(self, username):
        return bool(re.match(r'^[a-zA-Z0-9]{1,15}@mmust\.ac\.ke$', username))

class LogoutView(View):
    def get(self, request, *args, **kwargs):
        logout(request)  # Use logout directly
        return redirect('login')  # Redirect to the login page or another appropriate page
    
class ResetPasswordView(View):
    template_name = 'reset_password.html'
    form_class = PasswordResetForm

    def get(self, request):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']  # This is the email address
            user = System_User.objects.filter(username=username).first()
            if user:
                try:
                    # Generate a unique token
                    token = get_random_string(length=32)
                    # Save the token to the database
                    PasswordResetToken.objects.create(username=user, token=token)
                    # Generate the reset link
                    reset_link = request.build_absolute_uri(f'/reset-password/{token}/')
                    # Send password reset email
                    send_mail(
                        'Reset Your Password',
                        f'Click the link to reset your password: {reset_link}',
                        settings.EMAIL_HOST_USER,
                        [user.username],  # Use the username as the email address
                        fail_silently=False,
                    )
                    success_message = f"A password reset link has been sent to {user.username}."
                    return render(request, self.template_name, {'form': form, 'success_message': success_message})
                except Exception as e:
                    error_message = f"An error occurred: {str(e)} or Email Address does not exist in our records"
                    return render(request, self.template_name, {'form': form, 'error_message': error_message})
            else:
                error_message = "Email Address does not exist in our records."
                return render(request, self.template_name, {'form': form, 'error_message': error_message})

        return render(request, self.template_name, {'form': form})


class ResetPasswordConfirmView(View):
    template_name = 'reset_password_confirm.html'

    def get(self, request, token):
        form = ResetForm()
        password_reset_token = PasswordResetToken.objects.filter(token=token).first()

        if not password_reset_token or password_reset_token.is_expired():
            error_message = "Token is invalid or expired."
            return render(request, self.template_name, {'form': form, 'token': token, 'error_message': error_message})

        return render(request, self.template_name, {'form': form, 'token': token})

    def post(self, request, token):
        form = ResetForm(request.POST)
        password_reset_token = PasswordResetToken.objects.filter(token=token).first()

        if not password_reset_token or password_reset_token.is_expired():
            error_message = "Token is invalid or expired."
            return render(request, self.template_name, {'form': form, 'token': token, 'error_message': error_message})

        if form.is_valid():
            # Get user related to the token
            user = get_object_or_404(System_User, username=password_reset_token.username)
            form.save(user)  # Save the password to the user

            # Delete the token for security
            password_reset_token.delete()

            # Success message
            messages.success(request, "Your password has been reset successfully.")
            return render(request, self.template_name, {'form': form, 'token': token})

        # If form is not valid, show errors
        return render(request, self.template_name, {'form': form, 'token': token, 'error_message': "Invalid form submission."})

class COD_DashboardView(View):
    def get(self, request):
        username = request.session.get('username')
        if not username:
            return redirect('login')

        lecturer = Lecturer.objects.filter(username=username).first()
        if not lecturer:
            return redirect('login')

        user = System_User.objects.get(username=username)
        department = lecturer.department
        department_name = department.department_name

        # Set session variables if not set
        request.session.setdefault('department_code', str(department.department_code))
        request.session.setdefault('employee_no', lecturer.employee_no)

        # Total students in the department
        total_students = Student.objects.filter(course__program__department=department).count()

        # Total lecturers in the department
        total_lecturers_in_department = Lecturer.objects.filter(department=department).count()

        # Fetch UnitOfferings assigned to the current lecturer
        lecturer_unit_offerings = UnitOffering.objects.filter(lecturer=lecturer)

        # Unique units taught by the lecturer
        unit_ids = lecturer_unit_offerings.values_list('unit', flat=True).distinct()
        total_units_for_lecturer = unit_ids.count()

        # Complaints related to those unit offerings        
        related_complaints_count = Complaint.objects.filter(
            unit_offering__unit__department=department
        ).count()

        # List of courses in this department
        courses = Course.objects.filter(program__department=department)

        context = {
            'total_students': total_students,
            'total_lecturers_in_department': total_lecturers_in_department,
            'total_units_for_lecturer': total_units_for_lecturer,
            'related_complaints_count': related_complaints_count,
            'last_name': lecturer.last_name,
            'user': user,
            'units': Unit.objects.filter(pk__in=unit_ids),
            'courses': courses,
            'department_name': department_name,
        }

        return render(request, 'cod_dashboard.html', context)

class Exam_DashboardView(View):
    def get(self, request):
        username = request.session.get('username')
        if not username:
            return redirect('login')

        lecturer = Lecturer.objects.filter(username=username).first()
        if not lecturer:
            return redirect('login')

        user = System_User.objects.get(username=username)
        department = lecturer.department
        department_name = department.department_name

        # Set session variables if not set
        request.session.setdefault('department_code', str(department.department_code))
        request.session.setdefault('employee_no', lecturer.employee_no)

        # Total students in the department
        total_students = Student.objects.filter(course__program__department=department).count()

        # Total lecturers in the department
        total_lecturers_in_department = Lecturer.objects.filter(department=department).count()

        # Fetch UnitOfferings assigned to the current lecturer
        lecturer_unit_offerings = UnitOffering.objects.filter(lecturer=lecturer)

        # Unique units taught by the lecturer
        unit_ids = lecturer_unit_offerings.values_list('unit', flat=True).distinct()
        total_units_for_lecturer = unit_ids.count()

        # Complaints related to those unit offerings
        related_complaints_count = Complaint.objects.filter(assigned_lecturer=lecturer).count()

        # List of courses in this department
        courses = Course.objects.filter(program__department=department)

        context = {
            'total_students': total_students,
            'total_lecturers_in_department': total_lecturers_in_department,
            'total_units_for_lecturer': total_units_for_lecturer,
            'related_complaints_count': related_complaints_count,
            'last_name': lecturer.last_name,
            'user': user,
            'units': Unit.objects.filter(pk__in=unit_ids),
            'courses': courses,
            'department_name': department_name,
        }

        return render(request, 'exam_dashboard.html', context)
    
class Lecturer_DashboardView(View):
    def get(self, request):
        username = request.session.get('username')
        if not username:
            return redirect('login')

        lecturer = Lecturer.objects.filter(username=username).first()
        if not lecturer:
            return redirect('login')

        user = System_User.objects.get(username=username)
        department = lecturer.department
        department_name = department.department_name

        # Set session variables if not set
        request.session.setdefault('department_code', str(department.department_code))
        request.session.setdefault('employee_no', lecturer.employee_no)

        # Total students in the department
        total_students = Student.objects.filter(course__program__department=department).count()

        # Total lecturers in the department
        total_lecturers_in_department = Lecturer.objects.filter(department=department).count()

        # Fetch UnitOfferings assigned to the current lecturer
        lecturer_unit_offerings = UnitOffering.objects.filter(lecturer=lecturer)

        # Unique units taught by the lecturer
        unit_ids = lecturer_unit_offerings.values_list('unit', flat=True).distinct()
        total_units_for_lecturer = unit_ids.count()

        
        # Complaints related to those unit offerings
        related_complaints_count = Complaint.objects.filter(assigned_lecturer=lecturer).count()

        # List of courses in this department
        courses = Course.objects.filter(program__department=department)

        context = {
            'total_students': total_students,
            'total_lecturers_in_department': total_lecturers_in_department,
            'total_units_for_lecturer': total_units_for_lecturer,
            'related_complaints_count': related_complaints_count,
            'last_name': lecturer.last_name,
            'user': user,
            'units': Unit.objects.filter(pk__in=unit_ids),
            'courses': courses,
            'department_name': department_name,
        }

        return render(request, 'lecturer_dashboard.html', context)

class CodComplaintsView(View):
    def get(self, request):
        username = request.session.get('username')
        if not username:
            return redirect('login')

        try:
            cod = Lecturer.objects.get(username=username, role='COD')
            department = cod.department
            complaints = Complaint.objects.filter(
                unit_offering__unit__department=department,
                assigned_lecturer__isnull=True
            ).select_related('student', 'unit_offering__unit')
        except Lecturer.DoesNotExist:
            return redirect('login')

        context = {
            'complaints': complaints
        }
        return render(request, 'cod_complaints.html', context)


class AssignLecturerView(View):
    def get(self, request, complaint_code):
        username = request.session.get('username')
        if not username:
            return redirect('login')

        complaint = get_object_or_404(Complaint, complaint_code=complaint_code)
        cod = get_object_or_404(Lecturer, username=username, role='COD')

        # Query unit, student, and academic year details
        unit_offering = complaint.unit_offering
        unit = unit_offering.unit
        student = complaint.student
        academic_year = unit_offering.academic_year

        # Pass the necessary information to the template
        form = AssignLecturerForm(department=cod.department)

        return render(request, 'assign_lecturer.html', {
            'form': form,
            'complaint': complaint,
            'unit': unit,
            'student': student,
            'academic_year': academic_year,
        })

    def post(self, request, complaint_code):
        username = request.session.get('username')
        if not username:
            return redirect('login')

        complaint = get_object_or_404(Complaint, complaint_code=complaint_code)
        cod = get_object_or_404(Lecturer, username=username, role='COD')
        form = AssignLecturerForm(request.POST, department=cod.department)

        if form.is_valid():
            complaint.assigned_lecturer = form.cleaned_data['lecturer']
            complaint.save()
            messages.success(request, "Lecturer successfully assigned to the complaint.")
            return redirect('cod-complaints')

        return render(request, 'assign_lecturer.html', {
            'form': form,
            'complaint': complaint
        })

class CodRespondView(FormView):
    template_name = 'cod_response.html'
    form_class = ResponseForm

    def dispatch(self, request, *args, **kwargs):
        # Get complaint based on complaint_code from URL kwargs
        self.complaint = get_object_or_404(Complaint, complaint_code=kwargs['complaint_code'])
        # Ensure the complaint is not already resolved
        if self.complaint.resolved:
            messages.error(request, "This complaint has already been resolved.")
            return redirect('cod-complaints')
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        """Prepare initial form data based on the missing type of the complaint."""
        initial = super().get_initial()
        if self.complaint.missing_type == 'CAT':
            initial['exam_mark'] = None  # Set exam mark to None if missing type is CAT
        elif self.complaint.missing_type == 'EXAM':
            initial['cat_mark'] = None  # Set CAT mark to None if missing type is EXAM
        elif self.complaint.missing_type == 'BOTH':
            initial['cat_mark'] = None  # Set both to None if missing type is BOTH
            initial['exam_mark'] = None
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student_reg_no'] = self.complaint.student.reg_no
        context['unit_code'] = self.complaint.unit_offering.unit_code
        context['academic_year'] = self.complaint.unit_offering.academic_year.academic_year
        context['missing_type'] = self.complaint.missing_type  # Pass missing_type to template
        return context

    def form_valid(self, form):
        """Save the response, mark complaint as resolved, and redirect."""
        response = form.save(commit=False)
        response.student = self.complaint.student.reg_no
        response.unit_offering = self.complaint.unit_offering.unit_code
        response.academic_year = self.complaint.unit_offering.academic_year.academic_year
        response.save()

        # Mark the complaint as resolved
        self.complaint.resolved = True
        self.complaint.delete()

        # Success message and redirect
        messages.success(self.request, "Response submitted successfully.")
        return redirect('cod-complaints')

    def form_invalid(self, form):
        """Handle invalid form submission."""
        messages.error(self.request, "There was an error submitting the response.")
        return self.render_to_response(self.get_context_data(form=form))

class ExamComplaintsListView(ListView):
    model = Complaint
    template_name = 'exam_complaints.html'
    context_object_name = 'complaints'

    def get_queryset(self):
        """Return only unresolved complaints assigned to the logged-in lecturer."""
        username = self.request.session.get('username')
        if not username:
            return redirect('login')
        
        lecturer = Lecturer.objects.filter(username=username).first()
        if lecturer:
            return Complaint.objects.filter(assigned_lecturer=lecturer, resolved=False)
        return Complaint.objects.none()

class ExamRespondView(FormView):
    template_name = 'exam_respond.html'
    form_class = ResponseForm

    def dispatch(self, request, *args, **kwargs):
        # Get complaint based on complaint_code from URL kwargs
        self.complaint = get_object_or_404(Complaint, complaint_code=kwargs['complaint_code'])
        # Ensure the complaint is not already resolved
        if self.complaint.resolved:
            messages.error(request, "This complaint has already been resolved.")
            return redirect('exam-complaints')
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        """Prepare initial form data based on the missing type of the complaint."""
        initial = super().get_initial()
        if self.complaint.missing_type == 'CAT':
            initial['exam_mark'] = None  # Hide EXAM mark
        elif self.complaint.missing_type == 'EXAM':
            initial['cat_mark'] = None  # Hide CAT mark
        return initial

    def get_context_data(self, **kwargs):
        """Add complaint and missing type to context for use in template."""
        context = super().get_context_data(**kwargs)
        context['complaint'] = self.complaint
        return context

    def form_valid(self, form):
        """Save the response, mark complaint as resolved, and redirect."""
        response = form.save(commit=False)
        response.student = self.complaint.student.reg_no
        response.unit_offering = self.complaint.unit_offering.unit_code
        response.academic_year = self.complaint.unit_offering.academic_year.academic_year
        response.save()

        # Mark the complaint as resolved
        self.complaint.resolved = True
        self.complaint.delete()

        # Success message and redirect
        messages.success(self.request, "Response submitted successfully.")
        return redirect('exam-complaints')

    def form_invalid(self, form):
        """Handle invalid form submission."""
        messages.error(self.request, "There was an error submitting the response.")
        return self.render_to_response(self.get_context_data(form=form))

                                       
class LecturerComplaintsListView(ListView):
    model = Complaint
    template_name = 'lecturer_complaints.html'
    context_object_name = 'complaints'

    def get_queryset(self):
        """Return only unresolved complaints assigned to the logged-in lecturer."""
        username = self.request.session.get('username')
        if not username:
            return redirect('login')
        
        lecturer = Lecturer.objects.filter(username=username).first()
        if lecturer:
            return Complaint.objects.filter(assigned_lecturer=lecturer, resolved=False)
        return Complaint.objects.none()

class LecturerRespondView(FormView):
    template_name = 'lecturer_respond.html'
    form_class = ResponseForm

    def dispatch(self, request, *args, **kwargs):
        # Get complaint based on complaint_code from URL kwargs
        self.complaint = get_object_or_404(Complaint, complaint_code=kwargs['complaint_code'])
        # Ensure the complaint is not already resolved
        if self.complaint.resolved:
            messages.error(request, "This complaint has already been resolved.")
            return redirect('exam-complaints')
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        """Prepare initial form data based on the missing type of the complaint."""
        initial = super().get_initial()
        if self.complaint.missing_type == 'CAT':
            initial['exam_mark'] = None  # Hide EXAM mark
        elif self.complaint.missing_type == 'EXAM':
            initial['cat_mark'] = None  # Hide CAT mark
        return initial

    def get_context_data(self, **kwargs):
        """Add complaint and missing type to context for use in template."""
        context = super().get_context_data(**kwargs)
        context['complaint'] = self.complaint
        return context

    def form_valid(self, form):
        """Save the response, mark complaint as resolved, and redirect."""
        response = form.save(commit=False)
        response.student = self.complaint.student.reg_no
        response.unit_offering = self.complaint.unit_offering.unit_code
        response.academic_year = self.complaint.unit_offering.academic_year.academic_year
        response.save()

        # Mark the complaint as resolved
        self.complaint.resolved = True
        self.complaint.delete()

        # Success message and redirect
        messages.success(self.request, "Response submitted successfully.")
        return redirect('lecturer-complaints')

    def form_invalid(self, form):
        """Handle invalid form submission."""
        messages.error(self.request, "There was an error submitting the response.")
        return self.render_to_response(self.get_context_data(form=form))

class CODResponseListView(View):
    template_name = 'cod_responses_list.html'

    def get(self, request):
        # Ensure the user is logged in and is a COD
        username = request.session.get('username')
        if not username:
            return redirect('login')

        lecturer = Lecturer.objects.filter(username=username).first()
        if lecturer and lecturer.role == 'COD':
            # Get responses that are not approved by the COD
            responses = Response.objects.filter(complaint__unit_offering__unit__department=lecturer.department, approved_by_cod=False)
            return render(request, self.template_name, {'responses': responses})
        
        messages.error(request, "You do not have permission to access this page.")
        return redirect('login')


class CODApproveResponseView(View):
    form_class = CODCommentForm
    template_name = 'cod_approve_response.html'

    def get(self, request, response_id):
        # Ensure the user is logged in and is a COD
        username = request.session.get('username')
        if not username:
            return redirect('login')

        lecturer = Lecturer.objects.filter(username=username).first()
        if lecturer and lecturer.role == 'COD':
            # Get the response related to the complaint code
            response = Response.objects.filter(response_id=response_id).first()
            if response and not response.approved_by_cod:
                form = self.form_class()
                return render(request, self.template_name, {'form': form, 'response': response})
            messages.error(request, "This response has already been approved or does not exist.")
            return redirect('cod-responses-list')

        messages.error(request, "You do not have permission to access this page.")
        return redirect('login')

    def post(self, request, response_id):
        # Ensure the user is logged in and is a COD
        username = request.session.get('username')
        if not username:
            return redirect('login')

        lecturer = Lecturer.objects.filter(username=username).first()
        if lecturer and lecturer.role == 'COD':
            # Get the response related to the response id
            response = Response.objects.filter(response_id=response_id).first()
            if response and not response.approved_by_cod:
                form = self.form_class(request.POST)
                if form.is_valid():
                    # Add the COD comment and update the approval status
                    response.comment_by_cod = form.cleaned_data['comment']
                    response.approved_by_cod = True
                    response.save()

                    messages.success(request, "Response approved successfully.")
                    return redirect('cod-responses-list')
                else:
                    messages.error(request, "There was an error with your submission.")
                    return render(request, self.template_name, {'form': form, 'response': response})

        messages.error(request, "You do not have permission to access this page.")
        return redirect('login')

class ExamOfficerApprovedResponsesView(ListView):
    model = Response
    template_name = 'approved_responses.html'
    context_object_name = 'responses_by_department'

    def get_queryset(self):
        # Check if the username is in the session
        username = self.request.session.get('username')
        
        if not username:
            # If username is not in session, redirect to login
            return redirect('login')
        
        try:
            # Retrieve the lecturer using the username from session
            lecturer = Lecturer.objects.filter(username=username).first()
        except Lecturer.DoesNotExist:
            raise Http404("Lecturer not found")
        
        # Check if the user is an Exam Officer
        if lecturer.role != 'Exam Officer':
            raise Http404("You are not authorized to access this page.")
        
        # Retrieve the department and the school the Exam Officer belongs to
        department = lecturer.department
        school = department.school

        # Retrieve all departments in the same school
        departments_in_school = Department.objects.filter(school=school)

        # Prepare a dictionary to store the responses grouped by department
        responses_by_department = {}

        for department in departments_in_school:
            responses_by_department[department] = Response.objects.filter(
                unit_offering__unit__department=department,
                approved_by_cod=True
            )

        return responses_by_department

class DeleteResponseView(DeleteView):
    model = Response
    template_name = 'delete_response.html'
    success_url = reverse_lazy('approved-responses')

    def delete(self, request, *args, **kwargs):
        try:
            response = super().delete(request, *args, **kwargs)
            messages.success(request, "Response deleted successfully.")
            return response
        except Exception as e:
            messages.error(request, "Failed to delete response.")
            return redirect(self.success_url)
 
class LoadNominalRollView(View):
    def get(self, request):
        form = UploadFileForm()
        return render(request, 'load_nominal_roll.html', {'form': form})

    def post(self, request):
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            try:
                # Read the CSV or Excel file
                if file.name.endswith('.csv'):
                    data = pd.read_csv(file)
                elif file.name.endswith('.xlsx'):
                    data = pd.read_excel(file)
                else:
                    messages.error(request, 'Invalid file format. Please upload a CSV or Excel file.')
                    return render(request, 'load_nominal_roll.html', {'form': form})

                # Get the lecturer based on session username
                username = request.session.get('username')
                if not username:
                    return redirect('login')  # Redirect to login if not logged in
                lecturer = get_object_or_404(Lecturer, username=username)
                lec_no = lecturer.lec_no

                # Get unit codes related to the lecturer
                related_units = LecturerUnit.objects.filter(lec_no=lec_no).values_list('unit_code', 'academic_year')
                allowed_unit_codes = {(u[0], u[1]) for u in related_units}  # Set of tuples for fast lookup

                # Initialize error list
                errors = []

                # Process each row
                for index, row in data.iterrows():
                    try:
                        # Retrieve related instances
                        unit = Unit.objects.get(unit_code=row['unit_code'])
                        student = Student.objects.get(reg_no=row['reg_no'])
                        academic_year = AcademicYear.objects.get(academic_year=row['academic_year'])

                        # Check if the unit and academic year are allowed for this lecturer
                        if (unit.unit_code, academic_year.academic_year) not in allowed_unit_codes:
                            errors.append(f"Row {index + 1}: Unit {unit.unit_code} not assigned to this lecturer or wrong academic year.")
                            continue

                        # Check if entry already exists to avoid duplicates
                        if NominalRoll.objects.filter(unit_code=unit, reg_no=student, academic_year=academic_year).exists():
                            errors.append(f"Row {index + 1}: Duplicate entry in nominal roll for unit {unit.unit_code} and student {student.reg_no}.")
                            continue

                        # Create NominalRoll instance and save
                        nominal_roll = NominalRoll(
                            unit_code=unit,
                            reg_no=student,
                            academic_year=academic_year
                        )
                        nominal_roll.full_clean()  # Validate model instance
                        nominal_roll.save()

                    except (Unit.DoesNotExist, Student.DoesNotExist, AcademicYear.DoesNotExist):
                        errors.append(f"Row {index + 1}: Foreign key reference not found (unit, student, or academic year).")
                    except ValidationError as ve:
                        errors.append(f"Row {index + 1}: {ve}")
                    except Exception as e:
                        errors.append(f"Row {index + 1}: Unexpected error - {str(e)}")

                # Display success or error messages
                if errors:
                    for error in errors:
                        messages.error(request, error)
                else:
                    messages.success(request, 'Nominal roll loaded successfully.')

                return render(request, 'load_nominal_roll.html', {'form': form})

            except Exception as e:
                messages.error(request, f'An error occurred while processing the file: {str(e)}')
        else:
            messages.error(request, 'Invalid form submission.')

        return render(request, 'load_nominal_roll.html', {'form': form})

class LoadResultView(View):
    def get(self, request):
        form = UploadFileForm()
        return render(request, 'load_result.html', {'form': form})

    def post(self, request):
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            try:
                # Load file into a DataFrame
                if file.name.endswith('.csv'):
                    data = pd.read_csv(file)
                elif file.name.endswith('.xlsx'):
                    data = pd.read_excel(file)
                else:
                    messages.error(request, 'Invalid file format. Please upload a CSV or Excel file.')
                    return render(request, 'load_result.html', {'form': form})

                # Get the lecturer's username from session
                username = request.session.get('username')
                if not username:
                    return redirect('login')  # Redirect to login if not logged in
                lecturer = get_object_or_404(Lecturer, username=username)
                lec_no = lecturer.lec_no

                # Get the units and academic years assigned to this lecturer
                related_units = LecturerUnit.objects.filter(lec_no=lec_no).values_list('unit_code', 'academic_year')
                allowed_units = {(u[0], u[1]) for u in related_units}  # Set for fast lookup

                errors = []

                for index, row in data.iterrows():
                    try:
                        # Retrieve foreign key instances
                        unit = Unit.objects.get(unit_code=row['unit_code'])
                        student = Student.objects.get(reg_no=row['reg_no'])
                        academic_year = AcademicYear.objects.get(academic_year=row['academic_year'])

                        # Check if unit and academic year are allowed for this lecturer
                        if (unit.unit_code, academic_year.academic_year) not in allowed_units:
                            errors.append(f"Row {index + 1}: Unit {unit.unit_code} is not assigned to this lecturer.")
                            continue

                        # Check for duplicate entries
                        if Result.objects.filter(unit_code=unit, reg_no=student, academic_year=academic_year).exists():
                            errors.append(f"Row {index + 1}: Duplicate result entry for student {student.reg_no} in unit {unit.unit_code}.")
                            continue

                        # Check CAT and exam marks, ensuring they meet field constraints
                        cat = row['cat']
                        exam = row['exam']
                        if not (0 <= cat <= 30):
                            errors.append(f"Row {index + 1}: Invalid CAT mark ({cat}). It should be between 0 and 30.")
                            continue
                        if not (0 <= exam <= 70):
                            errors.append(f"Row {index + 1}: Invalid exam mark ({exam}). It should be between 0 and 70.")
                            continue

                        # Create and validate the Result instance
                        result = Result(
                            unit_code=unit,
                            reg_no=student,
                            academic_year=academic_year,
                            cat=cat,
                            exam=exam
                        )
                        result.full_clean()  # Validate the instance
                        result.save()  # Save to the database

                    except (Unit.DoesNotExist, Student.DoesNotExist, AcademicYear.DoesNotExist):
                        errors.append(f"Row {index + 1}: Foreign key references not found (unit, student, or academic year).")
                    except ValidationError as ve:
                        errors.append(f"Row {index + 1}: Validation error - {ve}")
                    except Exception as e:
                        errors.append(f"Row {index + 1}: Unexpected error - {str(e)}")

                # Display error or success messages
                if errors:
                    for error in errors:
                        messages.error(request, error)
                else:
                    messages.success(request, 'Results loaded successfully.')

                return render(request, 'load_result.html', {'form': form})

            except Exception as e:
                messages.error(request, f'An error occurred while processing the file: {str(e)}')
        else:
            messages.error(request, 'Invalid form submission.')

        return render(request, 'load_result.html', {'form': form})

class ResultListView(ListView):
    model = Result
    template_name = 'result_list.html'
    context_object_name = 'results'

    def get_queryset(self):
        # Get lecturer's lec_no from session username
        username = self.request.session.get('username')
        lecturer = get_object_or_404(Lecturer, username=username)

        # Get lec_no associated with the lecturer
        lec_no = lecturer.lec_no
        lec_units = LecturerUnit.objects.filter(lec_no=lec_no)

        # Base queryset filtered by lecturer's units
        queryset = Result.objects.filter(
            unit_code__in=[unit.unit_code for unit in lec_units]
        )

        # Filter by academic year, unit code, and reg_no if provided in request
        academic_year = self.request.GET.get('academic_year')
        unit_code = self.request.GET.get('unit_code')
        reg_no = self.request.GET.get('reg_no')
        sort_field = self.request.GET.get('sort', 'reg_no')  # Default sort by reg_no

        if academic_year:
            queryset = queryset.filter(academic_year__academic_year=academic_year)
        if unit_code:
            queryset = queryset.filter(unit_code__unit_code=unit_code)
        if reg_no:
            queryset = queryset.filter(reg_no=reg_no)

        return queryset.order_by(sort_field)  # Apply sorting

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['academic_years'] = AcademicYear.objects.all()  # To populate filter options
        return context

class NominalRollListView(ListView):
    model = NominalRoll
    template_name = 'nominal_roll_list.html'
    context_object_name = 'nominal_rolls'

    def get_queryset(self):
        username = self.request.session.get('username')
        lecturer = get_object_or_404(Lecturer, username=username)

        # Get lec_no associated with the lecturer
        lec_no = lecturer.lec_no
        lec_units = LecturerUnit.objects.filter(lec_no=lec_no)
        queryset = NominalRoll.objects.filter(
            unit_code__in=[unit.unit_code for unit in lec_units]
        )

        academic_year = self.request.GET.get('academic_year')
        unit_code = self.request.GET.get('unit_code')
        reg_no = self.request.GET.get('reg_no')
        sort_field = self.request.GET.get('sort', 'reg_no')

        if academic_year:
            queryset = queryset.filter(academic_year__academic_year=academic_year)
        if unit_code:
            queryset = queryset.filter(unit_code__unit_code=unit_code)
        if reg_no:
            queryset = queryset.filter(reg_no=reg_no, unit_code=unit_code, academic_year=academic_year)

        return queryset.order_by(sort_field)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['academic_years'] = AcademicYear.objects.all()
        return context

class Exam_LoadNominalRollView(View):
    def get(self, request):
        form = UploadFileForm()
        return render(request, 'exam_load_nominal_roll.html', {'form': form})

    def post(self, request):
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            try:
                # Read the CSV or Excel file
                if file.name.endswith('.csv'):
                    data = pd.read_csv(file)
                elif file.name.endswith('.xlsx'):
                    data = pd.read_excel(file)
                else:
                    messages.error(request, 'Invalid file format. Please upload a CSV or Excel file.')
                    return render(request, 'exam_load_nominal_roll.html', {'form': form})

                # Get the lecturer based on session username
                username = request.session.get('username')
                if not username:
                    return redirect('login')  # Redirect to login if not logged in
                lecturer = get_object_or_404(Lecturer, username=username)
                lec_no = lecturer.lec_no

                # Get unit codes related to the lecturer
                related_units = LecturerUnit.objects.filter(lec_no=lec_no).values_list('unit_code', 'academic_year')
                allowed_unit_codes = {(u[0], u[1]) for u in related_units}  # Set of tuples for fast lookup

                # Initialize error list
                errors = []

                # Process each row
                for index, row in data.iterrows():
                    try:
                        # Retrieve related instances
                        unit = Unit.objects.get(unit_code=row['unit_code'])
                        student = Student.objects.get(reg_no=row['reg_no'])
                        academic_year = AcademicYear.objects.get(academic_year=row['academic_year'])

                        # Check if the unit and academic year are allowed for this lecturer
                        if (unit.unit_code, academic_year.academic_year) not in allowed_unit_codes:
                            errors.append(f"Row {index + 1}: Unit {unit.unit_code} not assigned to this lecturer or wrong academic year.")
                            continue

                        # Check if entry already exists to avoid duplicates
                        if NominalRoll.objects.filter(unit_code=unit, reg_no=student, academic_year=academic_year).exists():
                            errors.append(f"Row {index + 1}: Duplicate entry in nominal roll for unit {unit.unit_code} and student {student.reg_no}.")
                            continue

                        # Create NominalRoll instance and save
                        nominal_roll = NominalRoll(
                            unit_code=unit,
                            reg_no=student,
                            academic_year=academic_year
                        )
                        nominal_roll.full_clean()  # Validate model instance
                        nominal_roll.save()

                    except (Unit.DoesNotExist, Student.DoesNotExist, AcademicYear.DoesNotExist):
                        errors.append(f"Row {index + 1}: Foreign key reference not found (unit, student, or academic year).")
                    except ValidationError as ve:
                        errors.append(f"Row {index + 1}: {ve}")
                    except Exception as e:
                        errors.append(f"Row {index + 1}: Unexpected error - {str(e)}")

                # Display success or error messages
                if errors:
                    for error in errors:
                        messages.error(request, error)
                else:
                    messages.success(request, 'Nominal roll loaded successfully.')

                return render(request, 'exam_load_nominal_roll.html', {'form': form})

            except Exception as e:
                messages.error(request, f'An error occurred while processing the file: {str(e)}')
        else:
            messages.error(request, 'Invalid form submission.')

        return render(request, 'exam_load_nominal_roll.html', {'form': form})

class Exam_LoadResultView(View):
    def get(self, request):
        form = UploadFileForm()
        return render(request, 'exam_load_result.html', {'form': form})

    def post(self, request):
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            try:
                # Load file into a DataFrame
                if file.name.endswith('.csv'):
                    data = pd.read_csv(file)
                elif file.name.endswith('.xlsx'):
                    data = pd.read_excel(file)
                else:
                    messages.error(request, 'Invalid file format. Please upload a CSV or Excel file.')
                    return render(request, 'exam_load_result.html', {'form': form})

                # Get the lecturer's username from session
                username = request.session.get('username')
                if not username:
                    return redirect('login')  # Redirect to login if not logged in
                lecturer = get_object_or_404(Lecturer, username=username)
                lec_no = lecturer.lec_no

                # Get the units and academic years assigned to this lecturer
                related_units = LecturerUnit.objects.filter(lec_no=lec_no).values_list('unit_code', 'academic_year')
                allowed_units = {(u[0], u[1]) for u in related_units}  # Set for fast lookup

                errors = []

                for index, row in data.iterrows():
                    try:
                        # Retrieve foreign key instances
                        unit = Unit.objects.get(unit_code=row['unit_code'])
                        student = Student.objects.get(reg_no=row['reg_no'])
                        academic_year = AcademicYear.objects.get(academic_year=row['academic_year'])

                        # Check if unit and academic year are allowed for this lecturer
                        if (unit.unit_code, academic_year.academic_year) not in allowed_units:
                            errors.append(f"Row {index + 1}: Unit {unit.unit_code} is not assigned to this lecturer.")
                            continue

                        # Check for duplicate entries
                        if Result.objects.filter(unit_code=unit, reg_no=student, academic_year=academic_year).exists():
                            errors.append(f"Row {index + 1}: Duplicate result entry for student {student.reg_no} in unit {unit.unit_code}.")
                            continue

                        # Check CAT and exam marks, ensuring they meet field constraints
                        cat = row['cat']
                        exam = row['exam']
                        if not (0 <= cat <= 30):
                            errors.append(f"Row {index + 1}: Invalid CAT mark ({cat}). It should be between 0 and 30.")
                            continue
                        if not (0 <= exam <= 70):
                            errors.append(f"Row {index + 1}: Invalid exam mark ({exam}). It should be between 0 and 70.")
                            continue

                        # Create and validate the Result instance
                        result = Result(
                            unit_code=unit,
                            reg_no=student,
                            academic_year=academic_year,
                            cat=cat,
                            exam=exam
                        )
                        result.full_clean()  # Validate the instance
                        result.save()  # Save to the database

                    except (Unit.DoesNotExist, Student.DoesNotExist, AcademicYear.DoesNotExist):
                        errors.append(f"Row {index + 1}: Foreign key references not found (unit, student, or academic year).")
                    except ValidationError as ve:
                        errors.append(f"Row {index + 1}: Validation error - {ve}")
                    except Exception as e:
                        errors.append(f"Row {index + 1}: Unexpected error - {str(e)}")

                # Display error or success messages
                if errors:
                    for error in errors:
                        messages.error(request, error)
                else:
                    messages.success(request, 'Results loaded successfully.')

                return render(request, 'exam_load_result.html', {'form': form})

            except Exception as e:
                messages.error(request, f'An error occurred while processing the file: {str(e)}')
        else:
            messages.error(request, 'Invalid form submission.')

        return render(request, 'exam_load_result.html', {'form': form})

class Exam_ResultListView(ListView):
    model = Result
    template_name = 'exam_result_list.html'
    context_object_name = 'results'

    def get_queryset(self):
        # Get lecturer's lec_no from session username
        username = self.request.session.get('username')
        lecturer = get_object_or_404(Lecturer, username=username)

        # Get lec_no associated with the lecturer
        lec_no = lecturer.lec_no
        lec_units = LecturerUnit.objects.filter(lec_no=lec_no)

        # Base queryset filtered by lecturer's units
        queryset = Result.objects.filter(
            unit_code__in=[unit.unit_code for unit in lec_units]
        )

        # Filter by academic year, unit code, and reg_no if provided in request
        academic_year = self.request.GET.get('academic_year')
        unit_code = self.request.GET.get('unit_code')
        reg_no = self.request.GET.get('reg_no')
        sort_field = self.request.GET.get('sort', 'reg_no')  # Default sort by reg_no

        if academic_year:
            queryset = queryset.filter(academic_year__academic_year=academic_year)
        if unit_code:
            queryset = queryset.filter(unit_code__unit_code=unit_code)
        if reg_no:
            queryset = queryset.filter(reg_no=reg_no)

        return queryset.order_by(sort_field)  # Apply sorting

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['academic_years'] = AcademicYear.objects.all()  # To populate filter options
        return context

class Exam_NominalRollListView(ListView):
    model = NominalRoll
    template_name = 'exam_nominal_roll_list.html'
    context_object_name = 'nominal_rolls'

    def get_queryset(self):
        username = self.request.session.get('username')
        lecturer = get_object_or_404(Lecturer, username=username)

        # Get lec_no associated with the lecturer
        lec_no = lecturer.lec_no
        lec_units = LecturerUnit.objects.filter(lec_no=lec_no)
        queryset = NominalRoll.objects.filter(
            unit_code__in=[unit.unit_code for unit in lec_units]
        )

        academic_year = self.request.GET.get('academic_year')
        unit_code = self.request.GET.get('unit_code')
        reg_no = self.request.GET.get('reg_no')
        sort_field = self.request.GET.get('sort', 'reg_no')

        if academic_year:
            queryset = queryset.filter(academic_year__academic_year=academic_year)
        if unit_code:
            queryset = queryset.filter(unit_code__unit_code=unit_code)
        if reg_no:
            queryset = queryset.filter(reg_no=reg_no, unit_code=unit_code, academic_year=academic_year)

        return queryset.order_by(sort_field)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['academic_years'] = AcademicYear.objects.all()
        return context

class COD_LoadNominalRollView(View):
    def get(self, request):
        form = UploadFileForm()
        return render(request, 'cod_load_nominal_roll.html', {'form': form})

    def post(self, request):
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            try:
                # Read the CSV or Excel file
                if file.name.endswith('.csv'):
                    data = pd.read_csv(file)
                elif file.name.endswith('.xlsx'):
                    data = pd.read_excel(file)
                else:
                    messages.error(request, 'Invalid file format. Please upload a CSV or Excel file.')
                    return render(request, 'cod_load_nominal_roll.html', {'form': form})

                # Get the lecturer based on session username
                username = request.session.get('username')
                if not username:
                    return redirect('login')  # Redirect to login if not logged in
                lecturer = get_object_or_404(Lecturer, username=username)
                lec_no = lecturer.lec_no

                # Get unit codes related to the lecturer
                related_units = LecturerUnit.objects.filter(lec_no=lec_no).values_list('unit_code', 'academic_year')
                allowed_unit_codes = {(u[0], u[1]) for u in related_units}  # Set of tuples for fast lookup

                # Initialize error list
                errors = []

                # Process each row
                for index, row in data.iterrows():
                    try:
                        # Retrieve related instances
                        unit = Unit.objects.get(unit_code=row['unit_code'])
                        student = Student.objects.get(reg_no=row['reg_no'])
                        academic_year = AcademicYear.objects.get(academic_year=row['academic_year'])

                        # Check if the unit and academic year are allowed for this lecturer
                        if (unit.unit_code, academic_year.academic_year) not in allowed_unit_codes:
                            errors.append(f"Row {index + 1}: Unit {unit.unit_code} not assigned to this lecturer or wrong academic year.")
                            continue

                        # Check if entry already exists to avoid duplicates
                        if NominalRoll.objects.filter(unit_code=unit, reg_no=student, academic_year=academic_year).exists():
                            errors.append(f"Row {index + 1}: Duplicate entry in nominal roll for unit {unit.unit_code} and student {student.reg_no}.")
                            continue

                        # Create NominalRoll instance and save
                        nominal_roll = NominalRoll(
                            unit_code=unit,
                            reg_no=student,
                            academic_year=academic_year
                        )
                        nominal_roll.full_clean()  # Validate model instance
                        nominal_roll.save()

                    except (Unit.DoesNotExist, Student.DoesNotExist, AcademicYear.DoesNotExist):
                        errors.append(f"Row {index + 1}: Foreign key reference not found (unit, student, or academic year).")
                    except ValidationError as ve:
                        errors.append(f"Row {index + 1}: {ve}")
                    except Exception as e:
                        errors.append(f"Row {index + 1}: Unexpected error - {str(e)}")

                # Display success or error messages
                if errors:
                    for error in errors:
                        messages.error(request, error)
                else:
                    messages.success(request, 'Nominal roll loaded successfully.')

                return render(request, 'cod_load_nominal_roll.html', {'form': form})

            except Exception as e:
                messages.error(request, f'An error occurred while processing the file: {str(e)}')
        else:
            messages.error(request, 'Invalid form submission.')

        return render(request, 'cod_load_nominal_roll.html', {'form': form})

class COD_LoadResultView(View):
    def get(self, request):
        form = UploadFileForm()
        return render(request, 'cod_load_result.html', {'form': form})

    def post(self, request):
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            try:
                # Load file into a DataFrame
                if file.name.endswith('.csv'):
                    data = pd.read_csv(file)
                elif file.name.endswith('.xlsx'):
                    data = pd.read_excel(file)
                else:
                    messages.error(request, 'Invalid file format. Please upload a CSV or Excel file.')
                    return render(request, 'cod_load_result.html', {'form': form})

                # Get the lecturer's username from session
                username = request.session.get('username')
                if not username:
                    return redirect('login')  # Redirect to login if not logged in
                lecturer = get_object_or_404(Lecturer, username=username)
                lec_no = lecturer.lec_no

                # Get the units and academic years assigned to this lecturer
                related_units = LecturerUnit.objects.filter(lec_no=lec_no).values_list('unit_code', 'academic_year')
                allowed_units = {(u[0], u[1]) for u in related_units}  # Set for fast lookup

                errors = []

                for index, row in data.iterrows():
                    try:
                        # Retrieve foreign key instances
                        unit = Unit.objects.get(unit_code=row['unit_code'])
                        student = Student.objects.get(reg_no=row['reg_no'])
                        academic_year = AcademicYear.objects.get(academic_year=row['academic_year'])

                        # Check if unit and academic year are allowed for this lecturer
                        if (unit.unit_code, academic_year.academic_year) not in allowed_units:
                            errors.append(f"Row {index + 1}: Unit {unit.unit_code} is not assigned to this lecturer.")
                            continue

                        # Check for duplicate entries
                        if Result.objects.filter(unit_code=unit, reg_no=student, academic_year=academic_year).exists():
                            errors.append(f"Row {index + 1}: Duplicate result entry for student {student.reg_no} in unit {unit.unit_code}.")
                            continue

                        # Check CAT and exam marks, ensuring they meet field constraints
                        cat = row['cat']
                        exam = row['exam']
                        if not (0 <= cat <= 30):
                            errors.append(f"Row {index + 1}: Invalid CAT mark ({cat}). It should be between 0 and 30.")
                            continue
                        if not (0 <= exam <= 70):
                            errors.append(f"Row {index + 1}: Invalid exam mark ({exam}). It should be between 0 and 70.")
                            continue

                        # Create and validate the Result instance
                        result = Result(
                            unit_code=unit,
                            reg_no=student,
                            academic_year=academic_year,
                            cat=cat,
                            exam=exam
                        )
                        result.full_clean()  # Validate the instance
                        result.save()  # Save to the database

                    except (Unit.DoesNotExist, Student.DoesNotExist, AcademicYear.DoesNotExist):
                        errors.append(f"Row {index + 1}: Foreign key references not found (unit, student, or academic year).")
                    except ValidationError as ve:
                        errors.append(f"Row {index + 1}: Validation error - {ve}")
                    except Exception as e:
                        errors.append(f"Row {index + 1}: Unexpected error - {str(e)}")

                # Display error or success messages
                if errors:
                    for error in errors:
                        messages.error(request, error)
                else:
                    messages.success(request, 'Results loaded successfully.')

                return render(request, 'cod_load_result.html', {'form': form})

            except Exception as e:
                messages.error(request, f'An error occurred while processing the file: {str(e)}')
        else:
            messages.error(request, 'Invalid form submission.')

        return render(request, 'cod_load_result.html', {'form': form})

class COD_ResultListView(ListView):
    model = Result
    template_name = 'cod_result_list.html'
    context_object_name = 'results'

    def get_queryset(self):
        # Get lecturer's lec_no from session username
        username = self.request.session.get('username')
        lecturer = get_object_or_404(Lecturer, username=username)

        # Get lec_no associated with the lecturer
        lec_no = lecturer.lec_no
        lec_units = LecturerUnit.objects.filter(lec_no=lec_no)

        # Base queryset filtered by lecturer's units
        queryset = Result.objects.filter(
            unit_code__in=[unit.unit_code for unit in lec_units]
        )

        # Filter by academic year, unit code, and reg_no if provided in request
        academic_year = self.request.GET.get('academic_year')
        unit_code = self.request.GET.get('unit_code')
        reg_no = self.request.GET.get('reg_no')
        sort_field = self.request.GET.get('sort', 'reg_no')  # Default sort by reg_no

        if academic_year:
            queryset = queryset.filter(academic_year__academic_year=academic_year)
        if unit_code:
            queryset = queryset.filter(unit_code__unit_code=unit_code)
        if reg_no:
            queryset = queryset.filter(reg_no=reg_no)

        return queryset.order_by(sort_field)  # Apply sorting

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['academic_years'] = AcademicYear.objects.all()  # To populate filter options
        return context

class COD_NominalRollListView(ListView):
    model = NominalRoll
    template_name = 'cod_nominal_roll_list.html'
    context_object_name = 'nominal_rolls'

    def get_queryset(self):
        username = self.request.session.get('username')
        lecturer = get_object_or_404(Lecturer, username=username)

        # Get lec_no associated with the lecturer
        lec_no = lecturer.lec_no
        lec_units = LecturerUnit.objects.filter(lec_no=lec_no)
        queryset = NominalRoll.objects.filter(
            unit_code__in=[unit.unit_code for unit in lec_units]
        )

        academic_year = self.request.GET.get('academic_year')
        unit_code = self.request.GET.get('unit_code')
        reg_no = self.request.GET.get('reg_no')
        sort_field = self.request.GET.get('sort', 'reg_no')

        if academic_year:
            queryset = queryset.filter(academic_year__academic_year=academic_year)
        if unit_code:
            queryset = queryset.filter(unit_code__unit_code=unit_code)
        if reg_no:
            queryset = queryset.filter(reg_no=reg_no, unit_code=unit_code, academic_year=academic_year)

        return queryset.order_by(sort_field)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['academic_years'] = AcademicYear.objects.all()
        return context
