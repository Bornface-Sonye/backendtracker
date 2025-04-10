from django.shortcuts import render, redirect
from django.views.generic.edit import FormView
from django.views.generic import TemplateView
from .forms import StudentSearchForm, MissingMarkComplaintForm
from .models import Student, UnitOffering, Complaint
import random
import string

from django.views.generic.edit import FormView
from .forms import MissingMarkComplaintForm
from django.shortcuts import render, redirect
from .models import Complaint, UnitOffering, Student
import random
import string


class StudentSearchView(FormView):
    template_name = 'student_search.html'
    form_class = StudentSearchForm
    success_url = '/submit/complaint/'

    def form_valid(self, form):
        reg_no = form.cleaned_data['reg_no']
        student = Student.objects.filter(registration_no=reg_no).first()

        if student:
            # Store data in session
            self.request.session['student_data'] = {
                'reg_no': reg_no,
                'course': form.cleaned_data['course'].id,
                'year_of_study': form.cleaned_data['year_of_study'],
                'academic_year': form.cleaned_data['academic_year'].id,
                'semester': form.cleaned_data['semester']
            }
            return super().form_valid(form)
        else:
            form.add_error('reg_no', 'Student not found.')
            return self.form_invalid(form)


from django.contrib import messages
from django.views.generic.edit import FormView
from .forms import MissingMarkComplaintForm
from django.shortcuts import render, redirect
from .models import Complaint, UnitOffering, Student
import random
import string

class ComplaintSubmissionView(FormView):
    template_name = 'submit_complaint.html'
    form_class = MissingMarkComplaintForm

    def form_valid(self, form):
        student_data = self.request.session.get('student_data')
        if not student_data:
            return redirect('student_search')  # Redirect if session data is missing

        # Retrieve data from session
        reg_no = student_data['reg_no']
        student = Student.objects.get(registration_no=reg_no)

        # Generate Complaint Code (system-generated)
        complaint_code = self.generate_complaint_code()

        # Get the selected unit offering
        unit_offering = form.cleaned_data['unit_offering']
        missing_mark = form.cleaned_data['missing_mark']

        # Save the complaint
        complaint = Complaint(
            complaint_code=complaint_code,
            student=student,
            unit_offering=unit_offering,
            missing_type=missing_mark
        )
        complaint.save()

        # Show success message
        messages.success(self.request, "Your complaint has been submitted successfully!")

        return self.render_to_response(self.get_context_data(form=form))

    def form_invalid(self, form):
        messages.error(self.request, "There was an error with your submission. Please check the form and try again.")
        return self.render_to_response(self.get_context_data(form=form))

    def generate_complaint_code(self):
        """ Generate a random complaint code """
        return 'CMP-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student_data = self.request.session.get('student_data')

        if student_data:
            # Filter units based on session data
            units = UnitOffering.objects.filter(
                course_id=student_data['course'],
                academic_year_id=student_data['academic_year'],
                semester=student_data['semester'],
                year_of_study=student_data['year_of_study']
            )
            context['units'] = units
        return context
