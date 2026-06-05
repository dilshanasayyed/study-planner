from django.contrib import admin

# Register your models here.
# planner/admin.py
"""
Django Admin Configuration

This allows you to manage data through Django's admin panel
Access at: http://127.0.0.1:8000/admin/
"""

from django.contrib import admin
from .models import (
    Subject, Topic, PDFDocument, StudyPlan,
    DailySchedule, ScheduledTopic, RevisionTask, UserProfile
)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    """Admin interface for Subject model"""
    list_display = ['name', 'user', 'total_topics', 'completed_topics', 'created_at']
    list_filter = ['created_at', 'user']
    search_fields = ['name', 'description', 'user__username']
    readonly_fields = ['created_at', 'total_topics', 'completed_topics']


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    """Admin interface for Topic model"""
    list_display = ['name', 'subject', 'importance', 'is_exam_critical', 
                   'estimated_hours', 'is_completed', 'order']
    list_filter = ['importance', 'is_exam_critical', 'is_completed', 'subject']
    search_fields = ['name', 'description', 'subject__name']
    list_editable = ['importance', 'is_exam_critical', 'estimated_hours', 'order']
    readonly_fields = ['created_at', 'completion_date']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('subject', 'pdf_source', 'name', 'description')
        }),
        ('Priority & Planning', {
            'fields': ('importance', 'is_exam_critical', 'estimated_hours', 'order')
        }),
        ('Completion', {
            'fields': ('is_completed', 'completion_date', 'notes')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )


@admin.register(PDFDocument)
class PDFDocumentAdmin(admin.ModelAdmin):
    """Admin interface for PDF documents"""
    list_display = ['title', 'user', 'subject', 'processing_status', 
                   'page_count', 'uploaded_at']
    list_filter = ['processing_status', 'uploaded_at', 'user']
    search_fields = ['title', 'user__username']
    readonly_fields = ['uploaded_at', 'page_count', 'extracted_text', 
                      'extracted_structure']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'subject', 'title', 'pdf_file')
        }),
        ('Processing', {
            'fields': ('processing_status', 'page_count')
        }),
        ('Extracted Content', {
            'fields': ('extracted_text', 'extracted_structure'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('uploaded_at',),
            'classes': ('collapse',)
        })
    )


@admin.register(StudyPlan)
class StudyPlanAdmin(admin.ModelAdmin):
    """Admin interface for Study Plans"""
    list_display = ['name', 'user', 'subject', 'exam_date', 
                   'daily_study_hours', 'is_active', 'created_at']
    list_filter = ['is_active', 'exam_date', 'created_at', 'user']
    search_fields = ['name', 'user__username', 'subject__name']
    readonly_fields = ['created_at', 'last_updated', 'total_days_available', 
                      'total_hours_available']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'subject', 'name')
        }),
        ('Schedule', {
            'fields': ('start_date', 'exam_date', 'daily_study_hours')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Calculated Values', {
            'fields': ('total_days_available', 'total_hours_available'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'last_updated'),
            'classes': ('collapse',)
        })
    )


@admin.register(DailySchedule)
class DailyScheduleAdmin(admin.ModelAdmin):
    """Admin interface for Daily Schedules"""
    list_display = ['study_plan', 'date', 'total_hours_planned', 'is_completed']
    list_filter = ['is_completed', 'date', 'study_plan']
    search_fields = ['study_plan__name']
    date_hierarchy = 'date'


@admin.register(ScheduledTopic)
class ScheduledTopicAdmin(admin.ModelAdmin):
    """Admin interface for Scheduled Topics"""
    list_display = ['topic', 'daily_schedule', 'allocated_hours', 
                   'order', 'is_completed']
    list_filter = ['is_completed']
    search_fields = ['topic__name', 'daily_schedule__study_plan__name']


@admin.register(RevisionTask)
class RevisionTaskAdmin(admin.ModelAdmin):
    """Admin interface for Revision Tasks"""
    list_display = ['topic', 'scheduled_date', 'revision_number', 
                   'is_completed', 'completed_date']
    list_filter = ['is_completed', 'revision_number', 'scheduled_date']
    search_fields = ['topic__name']
    date_hierarchy = 'scheduled_date'
    
    fieldsets = (
        ('Task Information', {
            'fields': ('topic', 'scheduled_date', 'revision_number')
        }),
        ('Completion', {
            'fields': ('is_completed', 'completed_date', 'notes')
        })
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin interface for User Profiles"""
    list_display = ['user', 'full_name', 'institution', 'course', 
                   'default_daily_hours', 'created_at']
    list_filter = ['created_at', 'institution']
    search_fields = ['user__username', 'full_name', 'institution', 'course']
    readonly_fields = ['created_at']


# Customize admin site
admin.site.site_header = "Study Planner Administration"
admin.site.site_title = "Study Planner Admin"
admin.site.index_title = "Welcome to Study Planner Admin Panel"