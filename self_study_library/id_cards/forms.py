from django import forms


class FindStudentForm(forms.Form):
    student_id = forms.CharField(max_length=20, label="Student ID", help_text="Example: LIB00012")
