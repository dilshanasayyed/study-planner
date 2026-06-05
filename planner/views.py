from django.shortcuts import render

# Create your views here.
# planner/views.py
"""
Django Views - Business Logic for Study Planner

This file contains all the view functions that handle:
- User requests
- Data processing
- Rendering templates
- Redirecting users
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Count, Q, Sum
from django.core.paginator import Paginator
from datetime import timedelta, datetime
import json

from .models import (
    Subject, Topic, PDFDocument, StudyPlan, 
    DailySchedule, ScheduledTopic, RevisionTask, UserProfile
)
from .forms import (
    SignUpForm, SubjectForm, PDFUploadForm, TopicForm,
    StudyPlanForm, TopicCompletionForm, BulkTopicEditForm, UserProfileForm
)
from .pdf_processor import process_pdf, extract_topics_from_structure
from .study_planner_algorithm import create_study_plan, calculate_progress


# =====================================================
# AUTHENTICATION VIEWS
# =====================================================

def signup_view(request):
    """
    User registration
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Welcome! Your account has been created.')
            return redirect('dashboard')
    else:
        form = SignUpForm()
    
    return render(request, 'planner/signup.html', {'form': form})


def login_view(request):
    """
    User login
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            
            # Redirect to next page if specified
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'planner/login.html')


def logout_view(request):
    """
    User logout
    """
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


# =====================================================
# DASHBOARD & HOME
# =====================================================

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Count

from .models import (
    Subject,
    Topic,
    StudyPlan,
    DailySchedule,
    ScheduledTopic,
    RevisionTask,
    PDFDocument,
)

@login_required
def dashboard(request):
    user = request.user
    today = timezone.now().date()

    # Subjects
    subjects = Subject.objects.filter(user=user)
    has_subjects = subjects.exists()

    # Topics & progress
    total_topics = Topic.objects.filter(subject__user=user).count()
    completed_topics = Topic.objects.filter(
        subject__user=user,
        is_completed=True
    ).count()

    overall_progress = round(
        (completed_topics / total_topics) * 100, 1
    ) if total_topics > 0 else 0

    # Active study plans
    active_plans = StudyPlan.objects.filter(
        user=user,
        is_active=True,
        exam_date__gte=today
    ).order_by('exam_date')[:5]

    # Today's schedule
    today_schedule = DailySchedule.objects.filter(
        study_plan__user=user,
        date=today
    ).first()

    # Pending revisions
    pending_revisions = RevisionTask.objects.filter(
        topic__subject__user=user,
        is_completed=False
    ).order_by('scheduled_date')

    pending_revision_count = pending_revisions.count()

    # Recent PDFs
    recent_pdfs = PDFDocument.objects.filter(
        user=user
    ).order_by('-uploaded_at')[:4]

    context = {
        'subjects': subjects,
        'has_subjects': has_subjects,
        'total_topics': total_topics,
        'completed_topics': completed_topics,
        'overall_progress': overall_progress,
        'active_plans': active_plans,
        'today_schedule': today_schedule,
        'pending_revisions': pending_revisions,
        'pending_revision_count': pending_revision_count,
        'recent_pdfs': recent_pdfs,
    }

    return render(request, 'planner/dashboard.html', context)
# =====================================================
# SUBJECT MANAGEMENT
# =====================================================

@login_required
def subject_list(request):
    """
    List all subjects for the user
    """
    subjects = Subject.objects.filter(user=request.user).annotate(
        topic_count=Count('topics'),
        completed_count=Count('topics', filter=Q(topics__is_completed=True))
    ).order_by('-created_at')
    
    return render(request, 'planner/subject_list.html', {
        'subjects': subjects
    })


@login_required
def subject_create(request):
    """
    Create a new subject
    """
    if request.method == 'POST':
        form = SubjectForm(request.POST)
        if form.is_valid():
            subject = form.save(commit=False)
            subject.user = request.user
            subject.save()
            messages.success(request, f'Subject "{subject.name}" created successfully!')
            return redirect('subject_detail', pk=subject.pk)
    else:
        form = SubjectForm()
    
    return render(request, 'planner/subject_form.html', {
        'form': form,
        'title': 'Create New Subject'
    })


@login_required
def subject_detail(request, pk):
    """
    View details of a specific subject
    """
    subject = get_object_or_404(Subject, pk=pk, user=request.user)
    
    # Get all topics for this subject
    topics = subject.topics.all().order_by('order', 'name')
    
    # Get PDFs for this subject
    pdfs = PDFDocument.objects.filter(subject=subject).order_by('-uploaded_at')
    
    # Get study plans
    study_plans = StudyPlan.objects.filter(subject=subject).order_by('-created_at')
    
    # Calculate progress
    progress = subject.get_progress_percentage()
    
    context = {
        'subject': subject,
        'topics': topics,
        'pdfs': pdfs,
        'study_plans': study_plans,
        'progress': progress,
    }
    
    return render(request, 'planner/subject_detail.html', context)


@login_required
def subject_edit(request, pk):
    """
    Edit an existing subject
    """
    subject = get_object_or_404(Subject, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = SubjectForm(request.POST, instance=subject)
        if form.is_valid():
            form.save()
            messages.success(request, 'Subject updated successfully!')
            return redirect('subject_detail', pk=subject.pk)
    else:
        form = SubjectForm(instance=subject)
    
    return render(request, 'planner/subject_form.html', {
        'form': form,
        'subject': subject,
        'title': 'Edit Subject'
    })


@login_required
def subject_delete(request, pk):
    """
    Delete a subject (with confirmation)
    """
    subject = get_object_or_404(Subject, pk=pk, user=request.user)
    
    if request.method == 'POST':
        subject_name = subject.name
        subject.delete()
        messages.success(request, f'Subject "{subject_name}" deleted.')
        return redirect('subject_list')
    
    return render(request, 'planner/subject_confirm_delete.html', {
        'subject': subject
    })


# =====================================================
# PDF MANAGEMENT
# =====================================================

@login_required
def pdf_upload(request):
    """
    Upload a PDF and extract topics
    """
    if request.method == 'POST':
        form = PDFUploadForm(request.user, request.POST, request.FILES)
        if form.is_valid():
            pdf_doc = form.save(commit=False)
            pdf_doc.user = request.user
            pdf_doc.processing_status = 'processing'
            pdf_doc.save()
            
            # Process PDF in background (or synchronously for now)
            try:
                result = process_pdf(pdf_doc.pdf_file.path)
                
                if result['success']:
                    # Save extracted data
                    pdf_doc.extracted_text = result['full_text']
                    pdf_doc.extracted_structure = result['structure']
                    pdf_doc.page_count = result['page_count']
                    pdf_doc.processing_status = 'completed'
                    pdf_doc.save()
                    
                    messages.success(request, 'PDF uploaded and processed successfully!')
                    return redirect('pdf_topics_review', pk=pdf_doc.pk)
                else:
                    pdf_doc.processing_status = 'failed'
                    pdf_doc.save()
                    messages.error(request, f'Error processing PDF: {result["error"]}')
            
            except Exception as e:
                pdf_doc.processing_status = 'failed'
                pdf_doc.save()
                messages.error(request, f'Error processing PDF: {str(e)}')
            
            return redirect('pdf_list')
    else:
        form = PDFUploadForm(user=request.user)
    
    return render(request, 'planner/pdf_upload.html', {
        'form': form
    })


@login_required
def pdf_list(request):
    """
    List all uploaded PDFs
    """
    pdfs = PDFDocument.objects.filter(user=request.user).order_by('-uploaded_at')
    
    return render(request, 'planner/pdf_list.html', {
        'pdfs': pdfs
    })


@login_required
def pdf_detail(request, pk):
    """
    View PDF details and extracted content
    """
    pdf = get_object_or_404(PDFDocument, pk=pk, user=request.user)
    
    # Get extracted topics
    extracted_topics = extract_topics_from_structure(pdf.extracted_structure)
    
    # Get created topics from this PDF
    created_topics = Topic.objects.filter(pdf_source=pdf)
    
    context = {
        'pdf': pdf,
        'extracted_topics': extracted_topics,
        'created_topics': created_topics,
    }
    
    return render(request, 'planner/pdf_detail.html', context)


@login_required
def pdf_topics_review(request, pk):
    """
    Review and edit topics extracted from PDF before creating them
    """
    pdf = get_object_or_404(PDFDocument, pk=pk, user=request.user)
    
    # Get extracted topics
    extracted_topics = extract_topics_from_structure(pdf.extracted_structure)
    
    if request.method == 'POST':
        # Process submitted topics
        selected_subject_id = request.POST.get('subject')
        subject = get_object_or_404(Subject, pk=selected_subject_id, user=request.user)
        
        created_count = 0
        
        # Loop through submitted topics
        for i in range(len(extracted_topics)):
            include = request.POST.get(f'topic_{i}_include')
            
            if include:  # Only create if checkbox is checked
                name = request.POST.get(f'topic_{i}_name', '').strip()
                importance = request.POST.get(f'topic_{i}_importance', 'medium')
                hours = request.POST.get(f'topic_{i}_hours', '2.0')
                
                if name:
                    Topic.objects.create(
                        subject=subject,
                        pdf_source=pdf,
                        name=name,
                        importance=importance,
                        estimated_hours=float(hours),
                        order=i
                    )
                    created_count += 1
        
        # Update subject counts
        subject.update_topic_counts()
        
        messages.success(request, f'{created_count} topics created successfully!')
        return redirect('subject_detail', pk=subject.pk)
    
    # GET request - show review form
    subjects = Subject.objects.filter(user=request.user)
    
    context = {
        'pdf': pdf,
        'extracted_topics': extracted_topics,
        'subjects': subjects,
    }
    
    return render(request, 'planner/pdf_topics_review.html', context)


@login_required
def pdf_delete(request, pk):
    """
    Delete a PDF
    """
    pdf = get_object_or_404(PDFDocument, pk=pk, user=request.user)
    
    if request.method == 'POST':
        pdf.delete()
        messages.success(request, 'PDF deleted successfully.')
        return redirect('pdf_list')
    
    return render(request, 'planner/pdf_confirm_delete.html', {
        'pdf': pdf
    })


# Continue in next part...

# planner/views_part2.py
"""
Django Views - Part 2
Topic, Study Plan, and Schedule Management
"""

# =====================================================
# TOPIC MANAGEMENT
# =====================================================

@login_required
def topic_create(request, subject_pk):
    """
    Create a new topic manually
    """
    subject = get_object_or_404(Subject, pk=subject_pk, user=request.user)
    
    if request.method == 'POST':
        form = TopicForm(request.POST)
        if form.is_valid():
            topic = form.save(commit=False)
            topic.subject = subject
            topic.save()
            
            # Update subject counts
            subject.update_topic_counts()
            
            messages.success(request, f'Topic "{topic.name}" created!')
            return redirect('subject_detail', pk=subject.pk)
    else:
        form = TopicForm()
    
    return render(request, 'planner/topic_form.html', {
        'form': form,
        'subject': subject,
        'title': 'Add New Topic'
    })


@login_required
def topic_edit(request, pk):
    """
    Edit an existing topic
    """
    topic = get_object_or_404(Topic, pk=pk, subject__user=request.user)
    
    if request.method == 'POST':
        form = TopicForm(request.POST, instance=topic)
        if form.is_valid():
            form.save()
            messages.success(request, 'Topic updated successfully!')
            return redirect('subject_detail', pk=topic.subject.pk)
    else:
        form = TopicForm(instance=topic)
    
    return render(request, 'planner/topic_form.html', {
        'form': form,
        'topic': topic,
        'title': 'Edit Topic'
    })


@login_required
def topic_delete(request, pk):
    """
    Delete a topic
    """
    topic = get_object_or_404(Topic, pk=pk, subject__user=request.user)
    subject = topic.subject
    
    if request.method == 'POST':
        topic.delete()
        subject.update_topic_counts()
        messages.success(request, 'Topic deleted.')
        return redirect('subject_detail', pk=subject.pk)
    
    return render(request, 'planner/topic_confirm_delete.html', {
        'topic': topic
    })


@login_required
def topic_complete(request, pk):
    """
    Mark a topic as completed
    """
    topic = get_object_or_404(Topic, pk=pk, subject__user=request.user)
    
    if request.method == 'POST':
        form = TopicCompletionForm(request.POST)
        if form.is_valid():
            notes = form.cleaned_data.get('notes', '')
            if notes:
                topic.notes = notes
            
            topic.mark_complete()
            messages.success(request, f'Great! Topic "{topic.name}" marked as completed.')
            return redirect('subject_detail', pk=topic.subject.pk)
    else:
        form = TopicCompletionForm()
    
    return render(request, 'planner/topic_complete.html', {
        'topic': topic,
        'form': form
    })


@login_required
def topic_uncomplete(request, pk):
    """
    Mark a completed topic as incomplete
    """
    topic = get_object_or_404(Topic, pk=pk, subject__user=request.user)
    
    topic.is_completed = False
    topic.completion_date = None
    topic.save()
    
    # Update subject counts
    topic.subject.update_topic_counts()
    
    messages.info(request, f'Topic "{topic.name}" marked as incomplete.')
    return redirect('subject_detail', pk=topic.subject.pk)


# =====================================================
# STUDY PLAN MANAGEMENT
# =====================================================

@login_required
def study_plan_create(request, subject_pk):
    """
    Create a new study plan for a subject
    """
    subject = get_object_or_404(Subject, pk=subject_pk, user=request.user)
    
    # Check if subject has topics
    if subject.topics.count() == 0:
        messages.warning(request, 'Please add some topics to the subject first.')
        return redirect('subject_detail', pk=subject.pk)
    
    if request.method == 'POST':
        form = StudyPlanForm(request.POST)
        if form.is_valid():
            study_plan = form.save(commit=False)
            study_plan.user = request.user
            study_plan.subject = subject
            study_plan.save()
            
            # Calculate availability
            study_plan.calculate_availability()
            
            # Generate schedule
            topics = subject.topics.filter(is_completed=False)
            result = create_study_plan(study_plan, topics)
            
            if result['success']:
                # Save daily schedules
                for day_data in result['daily_schedules']:
                    daily_schedule = DailySchedule.objects.create(
                        study_plan=study_plan,
                        date=day_data['date'],
                        total_hours_planned=day_data['total_hours']
                    )
                    
                    # Add topics to schedule
                    for i, topic_data in enumerate(day_data['topics']):
                        ScheduledTopic.objects.create(
                            daily_schedule=daily_schedule,
                            topic=topic_data['topic'],
                            allocated_hours=topic_data['hours'],
                            order=i
                        )
                
                messages.success(request, 'Study plan created successfully!')
                return redirect('study_plan_detail', pk=study_plan.pk)
            else:
                messages.error(request, f'Error creating schedule: {result["error"]}')
    else:
        form = StudyPlanForm()
    
    return render(request, 'planner/study_plan_form.html', {
        'form': form,
        'subject': subject,
        'title': 'Create Study Plan'
    })


@login_required
def study_plan_list(request):
    """
    List all study plans
    """
    plans = StudyPlan.objects.filter(user=request.user).select_related(
        'subject'
    ).order_by('-created_at')
    
    return render(request, 'planner/study_plan_list.html', {
        'plans': plans
    })


@login_required
def study_plan_detail(request, pk):
    """
    View study plan details and schedule
    """
    plan = get_object_or_404(StudyPlan, pk=pk, user=request.user)
    
    # Get progress statistics
    progress = calculate_progress(plan)
    
    # Get schedule for next 7 days
    today = timezone.now().date()
    week_schedules = DailySchedule.objects.filter(
        study_plan=plan,
        date__gte=today,
        date__lt=today + timedelta(days=7)
    ).prefetch_related('scheduledtopic_set__topic').order_by('date')
    
    # Get today's schedule specifically
    today_schedule = DailySchedule.objects.filter(
        study_plan=plan,
        date=today
    ).prefetch_related('scheduledtopic_set__topic').first()
    
    # Get all schedules (for calendar view)
    all_schedules = DailySchedule.objects.filter(
        study_plan=plan
    ).order_by('date')
    
    context = {
        'plan': plan,
        'progress': progress,
        'week_schedules': week_schedules,
        'today_schedule': today_schedule,
        'all_schedules': all_schedules,
    }
    
    return render(request, 'planner/study_plan_detail.html', context)


@login_required
def study_plan_calendar(request, pk):
    """
    Calendar view of study plan
    """
    plan = get_object_or_404(StudyPlan, pk=pk, user=request.user)
    
    # Get all schedules
    schedules = DailySchedule.objects.filter(
        study_plan=plan
    ).prefetch_related('scheduledtopic_set__topic').order_by('date')
    
    # Organize by month
    schedules_by_month = {}
    for schedule in schedules:
        month_key = schedule.date.strftime('%Y-%m')
        if month_key not in schedules_by_month:
            schedules_by_month[month_key] = []
        schedules_by_month[month_key].append(schedule)
    
    context = {
        'plan': plan,
        'schedules_by_month': schedules_by_month,
    }
    
    return render(request, 'planner/study_plan_calendar.html', context)


@login_required
def daily_schedule_detail(request, pk):
    """
    View a specific day's schedule
    """
    schedule = get_object_or_404(
        DailySchedule, 
        pk=pk, 
        study_plan__user=request.user
    )
    
    # Get scheduled topics
    scheduled_topics = ScheduledTopic.objects.filter(
        daily_schedule=schedule
    ).select_related('topic').order_by('order')
    
    context = {
        'schedule': schedule,
        'scheduled_topics': scheduled_topics,
    }
    
    return render(request, 'planner/daily_schedule_detail.html', context)


@login_required
def daily_schedule_complete(request, pk):
    """
    Mark a day's schedule as completed
    """
    schedule = get_object_or_404(
        DailySchedule,
        pk=pk,
        study_plan__user=request.user
    )
    
    schedule.is_completed = True
    schedule.save()
    
    messages.success(request, f'Schedule for {schedule.date} marked as completed!')
    return redirect('study_plan_detail', pk=schedule.study_plan.pk)


# # =====================================================
# # REVISION MANAGEMENT
# # =====================================================

@login_required
def revision_list(request):
    """
    List all revision tasks
    """
    today = timezone.now().date()
    
    # Pending revisions (due or overdue)
    pending = RevisionTask.objects.filter(
        topic__subject__user=request.user,
        is_completed=False,
        scheduled_date__lte=today
    ).select_related('topic', 'topic__subject').order_by('scheduled_date')
    
    # Upcoming revisions
    upcoming = RevisionTask.objects.filter(
        topic__subject__user=request.user,
        is_completed=False,
        scheduled_date__gt=today
    ).select_related('topic', 'topic__subject').order_by('scheduled_date')[:20]
    
    # Completed revisions (recent)
    completed = RevisionTask.objects.filter(
        topic__subject__user=request.user,
        is_completed=True
    ).select_related('topic', 'topic__subject').order_by('-completed_date')[:20]
    
    context = {
        'pending_revisions': pending,
        'upcoming_revisions': upcoming,
        'completed_revisions': completed,
    }
    
    return render(request, 'planner/revision_list.html', context)


@login_required
def revision_complete(request, pk):
    """
    Mark a revision as completed
    """
    revision = get_object_or_404(
        RevisionTask,
        pk=pk,
        topic__subject__user=request.user
    )
    
    if request.method == 'POST':
        notes = request.POST.get('notes', '')
        
        revision.is_completed = True
        revision.completed_date = timezone.now().date()
        revision.notes = notes
        revision.save()
        
        messages.success(request, f'Revision for "{revision.topic.name}" completed!')
        return redirect('revision_list')
    
    return render(request, 'planner/revision_complete.html', {
        'revision': revision
    })


# # =====================================================
# # PROFILE & SETTINGS
# # =====================================================

@login_required
def profile_view(request):
    """
    View and edit user profile
    """
    profile = request.user.profile

    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=profile)

    # Get user statistics
    stats = {
        'total_subjects': Subject.objects.filter(user=request.user).count(),
        'total_topics': Topic.objects.filter(subject__user=request.user).count(),
        'completed_topics': Topic.objects.filter(
            subject__user=request.user,
            is_completed=True
        ).count(),
        'total_pdfs': PDFDocument.objects.filter(user=request.user).count(),
        'active_plans': StudyPlan.objects.filter(
            user=request.user,
            is_active=True
        ).count(),
    }

    # ✅ PROGRESS PERCENTAGE (ADDED)
    if stats['total_topics'] > 0:
        progress_percent = round(
            (stats['completed_topics'] / stats['total_topics']) * 100
        )
    else:
        progress_percent = 0

    context = {
        'form': form,
        'profile': profile,
        'stats': stats,
        'progress_percent': progress_percent,  # ✅ ADD THIS
    }

    return render(request, 'planner/profile.html', context)


# =====================================================
# AJAX / API ENDPOINTS
# =====================================================

@login_required
def ajax_topic_reorder(request):
    """
    AJAX endpoint to reorder topics
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            topic_orders = data.get('topics', [])
            
            for item in topic_orders:
                topic_id = item['id']
                new_order = item['order']
                
                topic = Topic.objects.get(
                    pk=topic_id,
                    subject__user=request.user
                )
                topic.order = new_order
                topic.save()
            
            return JsonResponse({'success': True})
        
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    
    return JsonResponse({'success': False}, status=400)


@login_required
def ajax_schedule_progress(request, pk):
    """
    Get progress data for a schedule (for progress bars)
    """
    schedule = get_object_or_404(
        DailySchedule,
        pk=pk,
        study_plan__user=request.user
    )
    
    scheduled_topics = ScheduledTopic.objects.filter(
        daily_schedule=schedule
    )
    
    total = scheduled_topics.count()
    completed = scheduled_topics.filter(is_completed=True).count()
    
    return JsonResponse({
        'total': total,
        'completed': completed,
        'percentage': round((completed / total * 100) if total > 0 else 0, 1)
    })