# planner/forms.py
"""
Django Forms for Study Planner

Forms handle user input, validation, and data cleaning
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Subject, Topic, StudyPlan, PDFDocument, UserProfile
import datetime


class SignUpForm(UserCreationForm):
    """
    Extended user registration form with additional fields
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address'
        })
    )
    
    full_name = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Full Name (optional)'
        })
    )
    
    institution = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'College/Institution (optional)'
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'full_name', 'institution', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add CSS classes to default fields
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Username'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm Password'
        })
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        
        if commit:
            user.save()
            # Update profile with additional info
            profile = user.profile
            profile.full_name = self.cleaned_data.get('full_name', '')
            profile.institution = self.cleaned_data.get('institution', '')
            profile.save()
        
        return user


class SubjectForm(forms.ModelForm):
    """
    Form for creating/editing subjects
    """
    class Meta:
        model = Subject
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Anatomy, Physiology, Chemistry'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional description of the subject'
            })
        }


class PDFUploadForm(forms.ModelForm):
    """
    Form for uploading PDF documents
    """
    class Meta:
        model = PDFDocument
        fields = ['title', 'pdf_file', 'subject']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Anatomy Notes Chapter 1-5'
            }),
            'pdf_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'application/pdf'
            }),
            'subject': forms.Select(attrs={
                'class': 'form-control'
            })
        }
    
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter subjects to show only user's subjects
        if user:
            self.fields['subject'].queryset = Subject.objects.filter(user=user)
            self.fields['subject'].required = False
    
    def clean_pdf_file(self):
        """Validate PDF file"""
        pdf_file = self.cleaned_data.get('pdf_file')
        
        if pdf_file:
            # Check file extension
            if not pdf_file.name.endswith('.pdf'):
                raise ValidationError('Only PDF files are allowed.')
            
            # Check file size (limit to 50MB)
            if pdf_file.size > 50 * 1024 * 1024:
                raise ValidationError('PDF file size must be under 50MB.')
        
        return pdf_file


class TopicForm(forms.ModelForm):
    """
    Form for creating/editing topics
    """
    class Meta:
        model = Topic
        fields = [
            'name', 'description', 'importance', 
            'is_exam_critical', 'estimated_hours', 'order'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Topic name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Topic details (optional)'
            }),
            'importance': forms.Select(attrs={
                'class': 'form-control'
            }),
            'is_exam_critical': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'estimated_hours': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.5',
                'min': '0.5',
                'placeholder': '2.0'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': '0'
            })
        }
    
    def clean_estimated_hours(self):
        """Validate estimated hours"""
        hours = self.cleaned_data.get('estimated_hours')
        
        if hours is not None and hours <= 0:
            raise ValidationError('Estimated hours must be greater than 0.')
        
        if hours is not None and hours > 100:
            raise ValidationError('Estimated hours seems too high. Please enter a realistic value.')
        
        return hours


class StudyPlanForm(forms.ModelForm):
    """
    Form for creating study plans
    """
    class Meta:
        model = StudyPlan
        fields = ['name', 'exam_date', 'daily_study_hours', 'start_date']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Final Exam Study Plan'
            }),
            'exam_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'daily_study_hours': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.5',
                'min': '1',
                'max': '16',
                'placeholder': '4.0'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default start date to today
        if not self.instance.pk:
            self.fields['start_date'].initial = timezone.now().date()
    
    def clean(self):
        """Validate form data"""
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        exam_date = cleaned_data.get('exam_date')
        daily_hours = cleaned_data.get('daily_study_hours')
        
        # Validate dates
        if start_date and exam_date:
            if exam_date <= start_date:
                raise ValidationError('Exam date must be after start date.')
            
            # Check if exam is too far (more than 1 year)
            delta = exam_date - start_date
            if delta.days > 365:
                raise ValidationError('Study plan cannot exceed 1 year.')
            
            # Warn if exam is too soon (less than 3 days)
            if delta.days < 3:
                self.add_error('exam_date', 
                    'Exam is very soon! Consider adjusting dates or daily hours.')
        
        # Validate daily hours
        if daily_hours:
            if daily_hours < 1:
                raise ValidationError('Daily study hours must be at least 1 hour.')
            if daily_hours > 16:
                raise ValidationError('Daily study hours cannot exceed 16 hours. Please be realistic!')
        
        return cleaned_data


class TopicCompletionForm(forms.Form):
    """
    Simple form to mark a topic as complete with notes
    """
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Add notes about what you learned (optional)'
        }),
        label='Completion Notes'
    )


class BulkTopicEditForm(forms.Form):
    """
    Form for bulk editing topics extracted from PDF
    """
    topics_data = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )
    
    def __init__(self, extracted_topics=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if extracted_topics:
            # Dynamically create fields for each extracted topic
            for i, topic in enumerate(extracted_topics):
                self.fields[f'topic_{i}_name'] = forms.CharField(
                    initial=topic.get('name', ''),
                    widget=forms.TextInput(attrs={
                        'class': 'form-control',
                        'placeholder': 'Topic name'
                    })
                )
                
                self.fields[f'topic_{i}_importance'] = forms.ChoiceField(
                    choices=[
                        ('high', 'High'),
                        ('medium', 'Medium'),
                        ('low', 'Low')
                    ],
                    initial='medium',
                    widget=forms.Select(attrs={
                        'class': 'form-control form-control-sm'
                    })
                )
                
                self.fields[f'topic_{i}_hours'] = forms.DecimalField(
                    initial=2.0,
                    min_value=0.5,
                    max_value=50,
                    widget=forms.NumberInput(attrs={
                        'class': 'form-control form-control-sm',
                        'step': '0.5'
                    })
                )
                
                self.fields[f'topic_{i}_include'] = forms.BooleanField(
                    initial=True,
                    required=False,
                    widget=forms.CheckboxInput(attrs={
                        'class': 'form-check-input'
                    })
                )


class UserProfileForm(forms.ModelForm):
    """
    Form for editing user profile
    """
    class Meta:
        model = UserProfile
        fields = ['full_name', 'institution', 'course', 'default_daily_hours']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your full name'
            }),
            'institution': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your college/institution'
            }),
            'course': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., MBBS, B.Tech CSE'
            }),
            'default_daily_hours': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.5',
                'min': '1'
            })
        }


class DateRangeForm(forms.Form):
    """
    Form for filtering by date range
    """
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_date')
        end = cleaned_data.get('end_date')
        
        if start and end and end < start:
            raise ValidationError('End date must be after start date.')
        
        return cleaned_data