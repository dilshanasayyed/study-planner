# planner/study_planner_algorithm.py
"""
Study Planner Algorithm

This module contains the logic for:
1. Calculating available study time
2. Prioritizing topics based on importance
3. Allocating time to each topic
4. Creating daily schedules
5. Balancing the workload

The algorithm is rule-based and considers:
- Exam deadline
- Topic importance
- Available hours per day
- Topic estimated completion time
"""

from datetime import timedelta
from django.utils import timezone
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class StudyPlannerAlgorithm:
    """
    Creates optimized study schedules based on available time and topic priorities
    """
    
    def __init__(self, study_plan, topics):
        """
        Initialize the planner
        
        Args:
            study_plan: StudyPlan model instance
            topics: QuerySet of Topic objects to include in plan
        """
        self.study_plan = study_plan
        self.topics = list(topics)
        self.daily_schedules = []
        
        # Calculate basic parameters
        self.start_date = study_plan.start_date
        self.exam_date = study_plan.exam_date
        self.daily_hours = float(study_plan.daily_study_hours)
        
        # Calculate total days
        delta = self.exam_date - self.start_date
        self.total_days = max(1, delta.days)
        
        # Calculate total hours available
        self.total_hours = self.total_days * self.daily_hours
    
    def generate_schedule(self):
        """
        Main method to generate the complete study schedule
        
        Returns:
            list: List of daily schedule data
        """
        try:
            # Step 1: Calculate how much time each topic needs
            self.calculate_topic_weights()
            
            # Step 2: Allocate time to each topic
            self.allocate_time_to_topics()
            
            # Step 3: Distribute topics across days
            self.distribute_topics_to_days()
            
            # Step 4: Return the schedule
            return {
                'success': True,
                'daily_schedules': self.daily_schedules,
                'total_days': self.total_days,
                'total_hours': self.total_hours,
                'topics_scheduled': len(self.topics),
                'error': None
            }
        
        except Exception as e:
            logger.error(f"Error generating schedule: {str(e)}")
            return {
                'success': False,
                'daily_schedules': [],
                'error': str(e)
            }
    
    def calculate_topic_weights(self):
        """
        Calculate relative importance/weight of each topic
        
        Weight factors:
        - Importance level (high=3, medium=2, low=1)
        - Exam critical flag (adds +1)
        - Base estimated hours
        """
        for topic in self.topics:
            # Base weight from estimated hours
            base_hours = float(topic.estimated_hours)
            
            # Importance multiplier
            importance_multiplier = {
                'high': 1.5,
                'medium': 1.0,
                'low': 0.7
            }.get(topic.importance, 1.0)
            
            # Exam critical bonus
            exam_bonus = 1.3 if topic.is_exam_critical else 1.0
            
            # Calculate final weight (time needed)
            topic.calculated_hours = base_hours * importance_multiplier * exam_bonus
            
            # Store for later use
            if not hasattr(topic, '_weight_data'):
                topic._weight_data = {}
            
            topic._weight_data['base_hours'] = base_hours
            topic._weight_data['importance_multiplier'] = importance_multiplier
            topic._weight_data['exam_bonus'] = exam_bonus
            topic._weight_data['final_hours'] = topic.calculated_hours
    
    def allocate_time_to_topics(self):
        """
        Allocate available time proportionally to topics
        
        If total required time > available time:
        - Prioritize high-importance topics
        - Scale down low-importance topics
        
        If total required time < available time:
        - Add buffer time to important topics
        - Add revision time
        """
        # Calculate total hours needed
        total_needed = sum(t.calculated_hours for t in self.topics)
        
        if total_needed > self.total_hours:
            # Not enough time - need to compress
            self._compress_schedule(total_needed)
        else:
            # Enough time - can add buffers
            self._expand_schedule(total_needed)
    
    def _compress_schedule(self, total_needed):
        """
        Compress schedule when time is limited
        
        Strategy:
        1. Ensure high-priority topics get adequate time
        2. Reduce time for low-priority topics more aggressively
        """
        # Calculate compression ratio
        compression_ratio = self.total_hours / total_needed
        
        # Sort topics by priority
        sorted_topics = sorted(
            self.topics,
            key=lambda t: (
                t.is_exam_critical,
                {'high': 3, 'medium': 2, 'low': 1}.get(t.importance, 1)
            ),
            reverse=True
        )
        
        # Allocate time with priority protection
        remaining_hours = self.total_hours
        
        for topic in sorted_topics:
            if topic.is_exam_critical or topic.importance == 'high':
                # Protect important topics - compress less
                topic.allocated_hours = topic.calculated_hours * max(0.8, compression_ratio)
            elif topic.importance == 'medium':
                topic.allocated_hours = topic.calculated_hours * compression_ratio
            else:
                # Low priority - compress more
                topic.allocated_hours = topic.calculated_hours * min(0.5, compression_ratio)
            
            # Ensure minimum time per topic
            topic.allocated_hours = max(0.5, topic.allocated_hours)
            remaining_hours -= topic.allocated_hours
        
        # Adjust if we went over
        if remaining_hours < 0:
            # Proportionally reduce all topics slightly
            adjustment = self.total_hours / sum(t.allocated_hours for t in self.topics)
            for topic in self.topics:
                topic.allocated_hours *= adjustment
    
    def _expand_schedule(self, total_needed):
        """
        Expand schedule when there's extra time
        
        Strategy:
        1. Allocate base time to all topics
        2. Add buffer time to important topics
        3. Add revision time
        """
        extra_hours = self.total_hours - total_needed
        
        # First, allocate base calculated hours
        for topic in self.topics:
            topic.allocated_hours = topic.calculated_hours
        
        # Distribute extra time to important topics
        important_topics = [
            t for t in self.topics 
            if t.is_exam_critical or t.importance == 'high'
        ]
        
        if important_topics:
            bonus_per_topic = extra_hours / len(important_topics)
            for topic in important_topics:
                topic.allocated_hours += bonus_per_topic
    
    def distribute_topics_to_days(self):
        """
        Distribute topics across days to create daily schedules
        
        Strategy:
        1. Sort topics by priority
        2. Fill days one by one
        3. Try to complete topics in single session when possible
        4. Split larger topics across multiple days if needed
        """
        # Sort topics by priority
        sorted_topics = sorted(
            self.topics,
            key=lambda t: (
                not t.is_exam_critical,  # Exam critical first
                {'high': 0, 'medium': 1, 'low': 2}.get(t.importance, 1),
                t.order
            )
        )
        
        current_date = self.start_date
        topic_index = 0
        remaining_topic_hours = None
        current_topic = None
        
        # Generate schedule for each day until exam
        while current_date < self.exam_date and topic_index < len(sorted_topics):
            daily_hours_remaining = self.daily_hours
            day_topics = []
            
            while daily_hours_remaining > 0 and topic_index < len(sorted_topics):
                # Get current topic
                if current_topic is None:
                    current_topic = sorted_topics[topic_index]
                    remaining_topic_hours = current_topic.allocated_hours
                
                # Determine how much time to allocate today
                hours_to_allocate = min(remaining_topic_hours, daily_hours_remaining)
                
                # Add to today's schedule
                day_topics.append({
                    'topic': current_topic,
                    'hours': hours_to_allocate
                })
                
                # Update remaining hours
                remaining_topic_hours -= hours_to_allocate
                daily_hours_remaining -= hours_to_allocate
                
                # If topic is complete, move to next
                if remaining_topic_hours <= 0:
                    topic_index += 1
                    current_topic = None
            
            # Save this day's schedule
            if day_topics:
                self.daily_schedules.append({
                    'date': current_date,
                    'topics': day_topics,
                    'total_hours': sum(t['hours'] for t in day_topics)
                })
            
            # Move to next day
            current_date += timedelta(days=1)
    
    def get_schedule_summary(self):
        """
        Get a summary of the generated schedule
        
        Returns:
            dict: Summary statistics
        """
        if not self.daily_schedules:
            return None
        
        total_scheduled_hours = sum(
            day['total_hours'] for day in self.daily_schedules
        )
        
        topics_covered = set()
        for day in self.daily_schedules:
            for topic_data in day['topics']:
                topics_covered.add(topic_data['topic'].id)
        
        return {
            'total_days_scheduled': len(self.daily_schedules),
            'total_hours_scheduled': round(total_scheduled_hours, 2),
            'topics_covered': len(topics_covered),
            'average_hours_per_day': round(total_scheduled_hours / len(self.daily_schedules), 2),
            'schedule_efficiency': round((total_scheduled_hours / self.total_hours) * 100, 1)
        }


def create_study_plan(study_plan_obj, topics):
    """
    Convenience function to create a study plan
    
    Args:
        study_plan_obj: StudyPlan model instance
        topics: QuerySet or list of Topic objects
    
    Returns:
        dict: Generated schedule data
    """
    planner = StudyPlannerAlgorithm(study_plan_obj, topics)
    return planner.generate_schedule()


def recalculate_schedule(study_plan_obj):
    """
    Recalculate schedule for an existing study plan
    (useful when topics are added/removed or dates change)
    
    Args:
        study_plan_obj: StudyPlan model instance
    
    Returns:
        dict: Updated schedule data
    """
    # Get incomplete topics for this subject
    topics = study_plan_obj.subject.topics.filter(is_completed=False)
    
    # Generate new schedule
    planner = StudyPlannerAlgorithm(study_plan_obj, topics)
    return planner.generate_schedule()


def calculate_progress(study_plan_obj):
    """
    Calculate progress statistics for a study plan
    
    Args:
        study_plan_obj: StudyPlan model instance
    
    Returns:
        dict: Progress statistics
    """
    from django.db.models import Count, Q
    
    total_topics = study_plan_obj.subject.topics.count()
    completed_topics = study_plan_obj.subject.topics.filter(is_completed=True).count()
    
    # Calculate completion percentage
    completion_percentage = 0
    if total_topics > 0:
        completion_percentage = round((completed_topics / total_topics) * 100, 1)
    
    # Days remaining
    today = timezone.now().date()
    days_remaining = max(0, (study_plan_obj.exam_date - today).days)
    days_used = max(0, (today - study_plan_obj.start_date).days)
    
    # Topics by priority
    high_priority = study_plan_obj.subject.topics.filter(
        importance='high'
    ).count()
    
    high_priority_completed = study_plan_obj.subject.topics.filter(
        importance='high',
        is_completed=True
    ).count()
    
    return {
        'total_topics': total_topics,
        'completed_topics': completed_topics,
        'remaining_topics': total_topics - completed_topics,
        'completion_percentage': completion_percentage,
        'days_remaining': days_remaining,
        'days_used': days_used,
        'total_days': study_plan_obj.total_days_available,
        'high_priority_topics': high_priority,
        'high_priority_completed': high_priority_completed,
        'on_track': completion_percentage >= ((days_used / study_plan_obj.total_days_available) * 100)
    }