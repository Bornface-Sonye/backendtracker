from django.shortcuts import render, redirect
from django.views import View
from .forms import StudentForm, MissingMarkForm
from .models import Student, UnitOffering, Complaint, Course, YearOfStudy, AcademicYear, Semester
from django.contrib import messages
from .utils import generate_unique_complaint_code  # import the utility


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

            return redirect('missing_mark_select')

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
            return redirect('student_select')

        units = self.get_student_unit_queryset(student_data)

        form = MissingMarkForm()
        form.fields['unit'].queryset = units

        return render(request, 'post_complaint.html', {'form': form})

    def post(self, request):
        student_data = request.session.get('student_data')
        if not student_data:
            return redirect('student_select')

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
    

