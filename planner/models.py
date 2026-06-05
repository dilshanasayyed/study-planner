from django.db import models

# Create your models here.
# planner/models.py
"""
Database Models for Study Planner Application

This file defines the structure of data stored in the database.
Think of models as blueprints for database tables.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import json


class Subject(models.Model):
    """
    Represents a subject (e.g., Biology, Chemistry, Physics)
    Each subject is owned by a user and can have multiple topics
    """
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        help_text="The student who owns this subject"
    )
    name = models.CharField(
        max_length=200,
        help_text="Subject name (e.g., 'Anatomy', 'Physiology')"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Optional description of the subject"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this subject was created"
    )
    total_topics = models.IntegerField(
        default=0,
        help_text="Total number of topics in this subject"
    )
    completed_topics = models.IntegerField(
        default=0,
        help_text="Number of completed topics"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Subject"
        verbose_name_plural = "Subjects"
    
    def __str__(self):
        return f"{self.name} - {self.user.username}"
    
    def get_progress_percentage(self):
        """Calculate completion percentage"""
        if self.total_topics == 0:
            return 0
        return round((self.completed_topics / self.total_topics) * 100, 1)
    
    def update_topic_counts(self):
        """Update the count of total and completed topics"""
        self.total_topics = self.topics.count()
        self.completed_topics = self.topics.filter(is_completed=True).count()
        self.save()


class PDFDocument(models.Model):
    """
    Stores uploaded PDF files and their extracted content
    Can be any academic PDF - notes, syllabus, handouts, etc.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text="The student who uploaded this PDF"
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='pdfs',
        null=True,
        blank=True,
        help_text="Subject this PDF belongs to (optional)"
    )
    title = models.CharField(
        max_length=300,
        help_text="Title of the document"
    )
    pdf_file = models.FileField(
        upload_to='pdfs/',
        help_text="The actual PDF file"
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the PDF was uploaded"
    )
    extracted_text = models.TextField(
        blank=True,
        help_text="Full text extracted from PDF"
    )
    extracted_structure = models.JSONField(
        default=dict,
        blank=True,
        help_text="Structured data extracted from PDF (chapters, topics, etc.)"
    )
    processing_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='pending',
        help_text="Status of PDF processing"
    )
    page_count = models.IntegerField(
        default=0,
        help_text="Number of pages in the PDF"
    )
    
    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = "PDF Document"
        verbose_name_plural = "PDF Documents"
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"


class Topic(models.Model):
    """
    Represents a single study topic/chapter
    Can be extracted from PDF or manually added by user
    """
    IMPORTANCE_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]
    
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='topics',
        help_text="Subject this topic belongs to"
    )
    pdf_source = models.ForeignKey(
        PDFDocument,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='topics',
        help_text="PDF this topic was extracted from (if any)"
    )
    name = models.CharField(
        max_length=500,
        help_text="Topic name/title"
    )
    description = models.TextField(
        blank=True,
        help_text="Details about the topic"
    )
    importance = models.CharField(
        max_length=10,
        choices=IMPORTANCE_CHOICES,
        default='medium',
        help_text="How important is this topic"
    )
    is_exam_critical = models.BooleanField(
        default=False,
        help_text="Is this topic frequently asked in exams?"
    )
    estimated_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=2.0,
        help_text="Estimated time to complete (hours)"
    )
    order = models.IntegerField(
        default=0,
        help_text="Order in which topics should be studied"
    )
    is_completed = models.BooleanField(
        default=False,
        help_text="Has this topic been completed?"
    )
    completion_date = models.DateField(
        null=True,
        blank=True,
        help_text="When was this topic completed"
    )
    notes = models.TextField(
        blank=True,
        help_text="Student's personal notes on this topic"
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Topic"
        verbose_name_plural = "Topics"
    
    def __str__(self):
        return f"{self.name} - {self.subject.name}"
    
    def mark_complete(self):
        """Mark topic as completed and trigger revision scheduling"""
        self.is_completed = True
        self.completion_date = timezone.now().date()
        self.save()
        
        # Update subject counts
        self.subject.update_topic_counts()
        
        # Create revision schedule
        self.create_revision_schedule()
    
    def create_revision_schedule(self):
        """Create revision tasks after topic completion"""
        if not self.completion_date:
            return
        
        # Schedule revisions at 7, 21, and 45 days
        revision_intervals = [7, 21, 45]
        
        for interval in revision_intervals:
            revision_date = self.completion_date + timedelta(days=interval)
            
            # Check if revision already exists
            if not RevisionTask.objects.filter(
                topic=self,
                scheduled_date=revision_date
            ).exists():
                RevisionTask.objects.create(
                    topic=self,
                    scheduled_date=revision_date,
                    revision_number=revision_intervals.index(interval) + 1
                )


class StudyPlan(models.Model):
    """
    Main study plan for a subject/exam
    Contains the overall planning parameters
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text="The student who owns this plan"
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='study_plans',
        help_text="Subject this plan covers"
    )
    name = models.CharField(
        max_length=200,
        help_text="Name of the study plan"
    )
    exam_date = models.DateField(
        help_text="Target exam date"
    )
    daily_study_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=4.0,
        help_text="Hours available for study per day"
    )
    start_date = models.DateField(
        default=timezone.now,
        help_text="When to start studying"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Is this plan currently active?"
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    last_updated = models.DateTimeField(
        auto_now=True
    )
    total_days_available = models.IntegerField(
        default=0,
        help_text="Total days between start and exam"
    )
    total_hours_available = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Total study hours available"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Study Plan"
        verbose_name_plural = "Study Plans"
    
    def __str__(self):
        return f"{self.name} - {self.user.username}"
    
    def calculate_availability(self):
        """Calculate total days and hours available for study"""
        if self.exam_date and self.start_date:
            delta = self.exam_date - self.start_date
            self.total_days_available = max(0, delta.days)
            self.total_hours_available = self.total_days_available * float(self.daily_study_hours)
            self.save()
    
    def days_remaining(self):
        """Calculate days remaining until exam"""
        today = timezone.now().date()
        if self.exam_date >= today:
            return (self.exam_date - today).days
        return 0


class DailySchedule(models.Model):
    """
    Daily study schedule - what to study on each day
    """
    study_plan = models.ForeignKey(
        StudyPlan,
        on_delete=models.CASCADE,
        related_name='daily_schedules',
        help_text="Study plan this schedule belongs to"
    )
    date = models.DateField(
        help_text="Date for this schedule"
    )
    topics = models.ManyToManyField(
        Topic,
        through='ScheduledTopic',
        help_text="Topics scheduled for this day"
    )
    total_hours_planned = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Total hours planned for this day"
    )
    is_completed = models.BooleanField(
        default=False,
        help_text="Has this day's schedule been completed?"
    )
    notes = models.TextField(
        blank=True,
        help_text="Notes for this day"
    )
    
    class Meta:
        ordering = ['date']
        unique_together = ['study_plan', 'date']
        verbose_name = "Daily Schedule"
        verbose_name_plural = "Daily Schedules"
    
    def __str__(self):
        return f"{self.study_plan.name} - {self.date}"


class ScheduledTopic(models.Model):
    """
    Links topics to daily schedules with time allocation
    This is the "through" model for the many-to-many relationship
    """
    daily_schedule = models.ForeignKey(
        DailySchedule,
        on_delete=models.CASCADE,
        help_text="Daily schedule"
    )
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        help_text="Topic to study"
    )
    allocated_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Hours allocated for this topic on this day"
    )
    order = models.IntegerField(
        default=0,
        help_text="Order in which to study topics"
    )
    is_completed = models.BooleanField(
        default=False,
        help_text="Has this been completed?"
    )
    
    class Meta:
        ordering = ['order']
        verbose_name = "Scheduled Topic"
        verbose_name_plural = "Scheduled Topics"
    
    def __str__(self):
        return f"{self.topic.name} on {self.daily_schedule.date}"


class RevisionTask(models.Model):
    """
    Revision tasks scheduled after topic completion
    Follows the 7-21-45 day revision pattern
    """
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name='revisions',
        help_text="Topic to revise"
    )
    scheduled_date = models.DateField(
        help_text="When this revision is scheduled"
    )
    revision_number = models.IntegerField(
        help_text="Which revision is this (1, 2, or 3)"
    )
    is_completed = models.BooleanField(
        default=False,
        help_text="Has this revision been completed?"
    )
    completed_date = models.DateField(
        null=True,
        blank=True,
        help_text="When was this revision completed"
    )
    notes = models.TextField(
        blank=True,
        help_text="Revision notes"
    )
    
    class Meta:
        ordering = ['scheduled_date']
        verbose_name = "Revision Task"
        verbose_name_plural = "Revision Tasks"
    
    def __str__(self):
        return f"Revision {self.revision_number} - {self.topic.name} on {self.scheduled_date}"
    
    def is_due(self):
        """Check if this revision is due today"""
        return self.scheduled_date <= timezone.now().date()
    
    def is_overdue(self):
        """Check if this revision is overdue"""
        return self.scheduled_date < timezone.now().date() and not self.is_completed


class UserProfile(models.Model):
    """
    Extended user profile with additional settings
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    full_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Full name of the student"
    )
    institution = models.CharField(
        max_length=200,
        blank=True,
        help_text="College/Institution name"
    )
    course = models.CharField(
        max_length=200,
        blank=True,
        help_text="Course name (e.g., MBBS, B.Tech)"
    )
    default_daily_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=4.0,
        help_text="Default daily study hours"
    )
    timezone = models.CharField(
        max_length=50,
        default='Asia/Kolkata',
        help_text="User's timezone"
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
    
    def __str__(self):
        return f"{self.user.username}'s Profile"


# Signal to create user profile automatically when user is created
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create profile when new user is created"""
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save profile when user is saved"""
    if hasattr(instance, 'profile'):
        instance.profile.save()