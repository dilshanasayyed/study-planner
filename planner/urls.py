# planner/urls.py
"""
URL Configuration for Study Planner App

Maps URLs to view functions
"""

from django.urls import path
from . import views

urlpatterns = [
    # ==========================================
    # AUTHENTICATION
    # ==========================================
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # ==========================================
    # DASHBOARD & HOME
    # ==========================================
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # ==========================================
    # SUBJECTS
    # ==========================================
    path('subjects/', views.subject_list, name='subject_list'),
    path('subjects/create/', views.subject_create, name='subject_create'),
    path('subjects/<int:pk>/', views.subject_detail, name='subject_detail'),
    path('subjects/<int:pk>/edit/', views.subject_edit, name='subject_edit'),
    path('subjects/<int:pk>/delete/', views.subject_delete, name='subject_delete'),
    
    # ==========================================
    # PDF MANAGEMENT
    # ==========================================
    path('pdfs/', views.pdf_list, name='pdf_list'),
    path('pdfs/upload/', views.pdf_upload, name='pdf_upload'),
    path('pdfs/<int:pk>/', views.pdf_detail, name='pdf_detail'),
    path('pdfs/<int:pk>/review/', views.pdf_topics_review, name='pdf_topics_review'),
    path('pdfs/<int:pk>/delete/', views.pdf_delete, name='pdf_delete'),
    
    # ==========================================
    # TOPICS
    # ==========================================
    path('subjects/<int:subject_pk>/topics/create/', views.topic_create, name='topic_create'),
    path('topics/<int:pk>/edit/', views.topic_edit, name='topic_edit'),
    path('topics/<int:pk>/delete/', views.topic_delete, name='topic_delete'),
    path('topics/<int:pk>/complete/', views.topic_complete, name='topic_complete'),
    path('topics/<int:pk>/uncomplete/', views.topic_uncomplete, name='topic_uncomplete'),
    
    # ==========================================
    # STUDY PLANS
    # ==========================================
    path('plans/', views.study_plan_list, name='study_plan_list'),
    path('subjects/<int:subject_pk>/plans/create/', views.study_plan_create, name='study_plan_create'),
    path('plans/<int:pk>/', views.study_plan_detail, name='study_plan_detail'),
    path('plans/<int:pk>/calendar/', views.study_plan_calendar, name='study_plan_calendar'),
    
    # ==========================================
    # DAILY SCHEDULES
    # ==========================================
    path('schedules/<int:pk>/', views.daily_schedule_detail, name='daily_schedule_detail'),
    path('schedules/<int:pk>/complete/', views.daily_schedule_complete, name='daily_schedule_complete'),
    
    # ==========================================
    # REVISIONS
    # ==========================================
    path('revisions/', views.revision_list, name='revision_list'),
    path('revisions/<int:pk>/complete/', views.revision_complete, name='revision_complete'),
    
    # ==========================================
    # PROFILE
    # ==========================================
    path('profile/', views.profile_view, name='profile'),
    
    # ==========================================
    # AJAX / API
    # ==========================================
    path('ajax/topics/reorder/', views.ajax_topic_reorder, name='ajax_topic_reorder'),
    path('ajax/schedules/<int:pk>/progress/', views.ajax_schedule_progress, name='ajax_schedule_progress'),
]