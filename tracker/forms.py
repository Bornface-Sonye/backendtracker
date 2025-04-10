from django import forms
from .models import Student, UnitOffering, Complaint
from django.core.exceptions import ValidationError
from django.utils.crypto import get_random_string

class StudentSearchForm(forms.Form):
    reg_no = forms.CharField(max_length=50, required=True, label='Registration Number')
    course = forms.ModelChoiceField(queryset=Student.objects.none(), required=True, label='Course')  # Adjust to filter based on the course
    year_of_study = forms.ChoiceField(choices=[(1, 'Year 1'), (2, 'Year 2'), (3, 'Year 3'), (4, 'Year 4')], required=True, label='Year of Study')
    academic_year = forms.ModelChoiceField(queryset=Student.objects.none(), required=True, label='Academic Year')  # Adjust this as necessary
    semester = forms.ChoiceField(choices=[(1, 'Semester 1'), (2, 'Semester 2'), (3, 'Semester 3')], required=True, label='Semester')

class MissingMarkComplaintForm(forms.Form):
    unit_offering = forms.ModelChoiceField(queryset=UnitOffering.objects.none(), required=True, label='Unit')
    missing_mark = forms.ChoiceField(choices=[('CAT', 'CAT'), ('EXAM', 'EXAM'), ('BOTH', 'Both')], required=True, label='Missing Mark')
    cat_missing = forms.BooleanField(required=False, label="Missing CAT")
    exam_missing = forms.BooleanField(required=False, label="Missing EXAM")

    def clean(self):
        cleaned_data = super().clean()
        cat_missing = cleaned_data.get("cat_missing")
        exam_missing = cleaned_data.get("exam_missing")
        
        if not cat_missing and not exam_missing:
            raise ValidationError("You must select at least one missing mark type (CAT or EXAM).")

        if cat_missing and exam_missing:
            cleaned_data['missing_mark'] = 'BOTH'
        elif cat_missing:
            cleaned_data['missing_mark'] = 'CAT'
        elif exam_missing:
            cleaned_data['missing_mark'] = 'EXAM'

        return cleaned_data
