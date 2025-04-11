from django import forms
from .models import Course, AcademicYear, Semester, YearOfStudy, Unit, Student, UnitOffering

class StudentForm(forms.Form):
    registration_no = forms.CharField(max_length=50, label='Registration Number')
    course = forms.ModelChoiceField(queryset=Course.objects.all(), label='Course')
    year_of_study = forms.ModelChoiceField(queryset=YearOfStudy.objects.all(), label='Year of Study')
    academic_year = forms.ModelChoiceField(queryset=AcademicYear.objects.all(), label='Academic Year')
    semester = forms.ModelChoiceField(queryset=Semester.objects.all(), label='Semester')

class MissingMarkForm(forms.Form):
    unit = forms.ModelChoiceField(queryset=UnitOffering.objects.none(), label='Missing Unit')
    missing_mark_type = forms.MultipleChoiceField(
        choices=[('CAT', 'CAT'), ('EXAM', 'EXAM')],
        widget=forms.CheckboxSelectMultiple,
        label='Select Missing Marks'
    )
