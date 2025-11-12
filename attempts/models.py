from django.db import models
from django.contrib.auth.models import User
from exams.models import Exam
from groups.models import Group

class Attempt(models.Model):
    STATUS_CHOICES = [
        ('in_progress', 'Jarayonda'),
        ('submitted', 'Yuborilgan'),
        ('completed', 'Yakunlangan'),
    ]
    
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attempts')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    
    # Scores
    reading_score = models.FloatField(null=True, blank=True)
    listening_score = models.FloatField(null=True, blank=True)
    writing_score = models.FloatField(null=True, blank=True)
    speaking_score = models.FloatField(null=True, blank=True)
    total_score = models.FloatField(null=True, blank=True)
    
    correct_count = models.IntegerField(default=0)
    incorrect_count = models.IntegerField(default=0)

    # Answers
    answers = models.JSONField(default=dict, blank=True)
    
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['exam', 'student']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.exam.title} ({self.status})"
    
    @property
    def is_completed(self):
        return self.status == 'completed'
    
    @property
    def duration_minutes(self):
        if self.completed_at and self.started_at:
            duration = self.completed_at - self.started_at
            return round(duration.total_seconds() / 60, 1)
        return 0

class AttemptAudio(models.Model):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name='audio_files')
    part_id = models.IntegerField(help_text="Speaking part ID")
    audio_file = models.FileField(upload_to='speaking_audios/%Y/%m/%d/')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['attempt', 'part_id']
        ordering = ['part_id']
    
    def __str__(self):
        return f"{self.attempt.student.get_full_name()} - Part {self.part_id}"

class Review(models.Model):
    attempt = models.OneToOneField(Attempt, on_delete=models.CASCADE, related_name='review')
    mentor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    
    # Writing/Speaking criteria
    task_achievement = models.FloatField(null=True, blank=True)
    coherence_cohesion = models.FloatField(null=True, blank=True)
    lexical_resource = models.FloatField(null=True, blank=True)
    grammatical_range = models.FloatField(null=True, blank=True)
    
    # Overall score
    overall_score = models.FloatField()
    
    # Detailed feedback
    feedback = models.TextField()
    strengths = models.TextField(blank=True, help_text="Talabaning kuchli tomonlari")
    improvements = models.TextField(blank=True, help_text="Takomillashtirish joylari")
    
    reviewed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-reviewed_at']
    
    def __str__(self):
        return f"Baholash: {self.attempt.student.get_full_name()} - {self.attempt.exam.title}"
    
    @property
    def criteria_scores(self):
        return {
            'task_achievement': self.task_achievement,
            'coherence_cohesion': self.coherence_cohesion,
            'lexical_resource': self.lexical_resource,
            'grammatical_range': self.grammatical_range,
        }