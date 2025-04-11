from django import forms
from .models import Course, AcademicYear, Semester, YearOfStudy, System_User, Student, UnitOffering


class SignUpForm(forms.ModelForm):
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password', 'class': 'form-control'})
    )
    class Meta:
        model = System_User
        fields = ['username', 'password_hash']
        labels = {
            'username': 'Username',
            'password_hash': 'Password',
            'confirm_password': 'Confirm Password',
        }
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Username eg awaliaro@mmust.ac.ke'}),
            'password_hash': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter Password'}),
            'confirm_password': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password_hash")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise forms.ValidationError("Password and confirm password do not match")

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.set_password(self.cleaned_data["password_hash"])
        if commit:
            instance.save()
        return instance

class LoginForm(forms.Form):
    username = forms.CharField(
        label="Username",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your Username:'})
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter your password:'})
    )

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get("username")
        password = cleaned_data.get("password")
        return cleaned_data
    
class PasswordResetForm(forms.Form):
    username = forms.EmailField(
        label='Username',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email address(Username)'})
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not System_User.objects.filter(username=username).exists():
            raise forms.ValidationError("This Username is not associated with any account.")
        return username

class ResetForm(forms.Form):  # Use forms.Form instead of ModelForm
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Password', 'class': 'form-control'}),
        label="Password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password', 'class': 'form-control'}),
        label="Confirm Password"
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise forms.ValidationError("Password and confirm password do not match.")

    def save(self, user, commit=True):
        # Use user object and set password
        user.set_password(self.cleaned_data["password"])  # Hash password and set it
        if commit:
            user.save()
        return user

class UploadFileForm(forms.Form):
    file = forms.FileField(label='Select a CSV or Excel file')


class StudentForm(forms.Form):
    reg_no = forms.CharField(max_length=50, label='Registration Number')
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
