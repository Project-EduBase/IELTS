from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Q
from .models import Attempt, Review, AttemptAudio


class AttemptAudioInline(admin.TabularInline):
    model = AttemptAudio
    extra = 1
    fields = ['part_id', 'audio_file', 'created_at']
    readonly_fields = ['created_at']


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    inlines = [AttemptAudioInline]

    list_display = [
        'get_student_name',
        'get_exam_title',
        'get_group_name',
        'get_status_badge',
        'get_total_score',
        'get_created_date'
    ]

    list_filter = [
        'status',
        'exam__section_type',
        'created_at',
        'group'
    ]

    search_fields = [
        'student__first_name',
        'student__last_name',
        'student__username',
        'exam__title',
        'group__name'
    ]

    readonly_fields = [
        'created_at',
        'started_at',
        'submitted_at',
        'completed_at',
        'get_student_info',
        'get_exam_info',
        'get_scores_info'
    ]

    fieldsets = (
        ('Asosiy Ma\'lumotlar', {
            'fields': ('get_student_info', 'get_exam_info', 'group', 'status')
        }),
        ('Balllar', {
            'fields': (
                'reading_score',
                'listening_score',
                'writing_score',
                'speaking_score',
                'total_score',
                'get_scores_info'
            ),
            'classes': ('collapse',)
        }),
        ('Javoblar', {
            'fields': ('correct_count', 'incorrect_count', 'answers'),
            'classes': ('collapse',)
        }),
        ('Vaqt Ma\'lumotlari', {
            'fields': ('started_at', 'submitted_at', 'completed_at', 'created_at'),
            'classes': ('collapse',)
        }),
    )

    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    actions = ['mark_as_submitted', 'mark_as_completed']

    def get_student_name(self, obj):
        """Talabaning to'liq ismini ko'rsatadi"""
        full_name = f"{obj.student.first_name} {obj.student.last_name}".strip()
        return full_name or obj.student.username
    get_student_name.short_description = 'Talaba'

    def get_exam_title(self, obj):
        """Imtihon nomini ko'rsatadi"""
        return obj.exam.title
    get_exam_title.short_description = 'Imtihon'

    def get_group_name(self, obj):
        """Guruh nomini ko'rsatadi"""
        return obj.group.name if obj.group else '-'
    get_group_name.short_description = 'Guruh'

    def get_status_badge(self, obj):
        """Status ni rang bilan ko'rsatadi"""
        colors = {
            'in_progress': '#FFA500',  # Orange
            'submitted': '#4169E1',    # Blue
            'completed': '#228B22',    # Green
        }
        color = colors.get(obj.status, '#808080')
        status_text = dict(obj.STATUS_CHOICES).get(obj.status, obj.status)
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            status_text
        )
    get_status_badge.short_description = 'Status'

    def get_total_score(self, obj):
        """Umumiy ballni ko'rsatadi"""
        if obj.total_score is not None:
            return format_html(
                '<span style="font-weight: bold; color: #228B22;">{} / 9.0</span>',
                obj.total_score
            )
        return '-'
    get_total_score.short_description = 'Umumiy Ball'

    def get_created_date(self, obj):
        """Yaratilgan sanani ko'rsatadi"""
        return obj.created_at.strftime('%d.%m.%Y %H:%M')
    get_created_date.short_description = 'Yaratilgan'

    def get_student_info(self, obj):
        """Talaba haqida to'liq ma\'lumot"""
        return format_html(
            '<strong>Ism:</strong> {} {}<br>'
            '<strong>Username:</strong> {}<br>'
            '<strong>Email:</strong> {}',
            obj.student.first_name,
            obj.student.last_name,
            obj.student.username,
            obj.student.email
        )
    get_student_info.short_description = 'Talaba Ma\'lumotlari'

    def get_exam_info(self, obj):
        """Imtihon haqida ma\'lumot"""
        return format_html(
            '<strong>Nomi:</strong> {}<br>'
            '<strong>Turi:</strong> {}',
            obj.exam.title,
            obj.exam.section_type
        )
    get_exam_info.short_description = 'Imtihon Ma\'lumotlari'

    def get_scores_info(self, obj):
        """Barcha balllarni ko\'rsatadi"""
        return format_html(
            '<strong>O\'qish:</strong> {}<br>'
            '<strong>Tinglash:</strong> {}<br>'
            '<strong>Yozish:</strong> {}<br>'
            '<strong>Gapirish:</strong> {}<br>'
            '<strong>Umumiy:</strong> <span style="color: #228B22; font-weight: bold;">{}</span>',
            obj.reading_score or '-',
            obj.listening_score or '-',
            obj.writing_score or '-',
            obj.speaking_score or '-',
            obj.total_score or '-'
        )
    get_scores_info.short_description = 'Balllar'

    def mark_as_submitted(self, request, queryset):
        """Statusni 'Submitted' ga o'zgartiradi"""
        updated = queryset.update(status='submitted')
        self.message_user(request, f'{updated} ta urinish "Submitted" statusiga o\'zgartirildi.')
    mark_as_submitted.short_description = 'Tanlangan urinishlarni "Submitted" qil'

    def mark_as_completed(self, request, queryset):
        """Statusni 'Completed' ga o'zgartiradi"""
        updated = queryset.update(status='completed')
        self.message_user(request, f'{updated} ta urinish "Completed" statusiga o\'zgartirildi.')
    mark_as_completed.short_description = 'Tanlangan urinishlarni "Completed" qil'


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = [
        'get_student_name',
        'get_exam_title',
        'get_mentor_name',
        'get_overall_score_badge',
        'get_reviewed_date'
    ]

    list_filter = [
        'reviewed_at',
        'overall_score',
        'attempt__exam__section_type'
    ]

    search_fields = [
        'attempt__student__first_name',
        'attempt__student__last_name',
        'attempt__student__username',
        'attempt__exam__title',
        'mentor__first_name',
        'mentor__last_name',
        'mentor__username'
    ]

    readonly_fields = [
        'reviewed_at',
        'get_attempt_info',
        'get_mentor_info',
        'get_scores_breakdown'
    ]

    fieldsets = (
        ('Asosiy Ma\'lumotlar', {
            'fields': ('get_attempt_info', 'get_mentor_info')
        }),
        ('Balllar', {
            'fields': (
                'task_achievement',
                'coherence_cohesion',
                'lexical_resource',
                'grammatical_range',
                'overall_score',
                'get_scores_breakdown'
            )
        }),
        ('Fikr-Mulohaza', {
            'fields': ('feedback',)
        }),
        ('Vaqt Ma\'lumotlari', {
            'fields': ('reviewed_at',),
            'classes': ('collapse',)
        }),
    )

    ordering = ['-reviewed_at']
    date_hierarchy = 'reviewed_at'

    def get_student_name(self, obj):
        """Talabaning to'liq ismini ko'rsatadi"""
        full_name = f"{obj.attempt.student.first_name} {obj.attempt.student.last_name}".strip()
        return full_name or obj.attempt.student.username
    get_student_name.short_description = 'Talaba'

    def get_exam_title(self, obj):
        """Imtihon nomini ko'rsatadi"""
        return obj.attempt.exam.title
    get_exam_title.short_description = 'Imtihon'

    def get_mentor_name(self, obj):
        """Mentorning to'liq ismini ko'rsatadi"""
        full_name = f"{obj.mentor.first_name} {obj.mentor.last_name}".strip()
        return full_name or obj.mentor.username
    get_mentor_name.short_description = 'Mentor'

    def get_overall_score_badge(self, obj):
        """Umumiy ballni rang bilan ko'rsatadi"""
        score = obj.overall_score
        if score >= 80:
            color = '#228B22'  # Green
        elif score >= 60:
            color = '#4169E1'  # Blue
        elif score >= 40:
            color = '#FFA500'  # Orange
        else:
            color = '#DC143C'  # Red

        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{} / 9.0</span>',
            color,
            score
        )
    get_overall_score_badge.short_description = 'Umumiy Ball'

    def get_reviewed_date(self, obj):
        """Tekshirilgan sanani ko'rsatadi"""
        return obj.reviewed_at.strftime('%d.%m.%Y %H:%M')
    get_reviewed_date.short_description = 'Tekshirilgan'

    def get_attempt_info(self, obj):
        """Urinish haqida ma\'lumot"""
        return format_html(
            '<strong>Talaba:</strong> {} {}<br>'
            '<strong>Imtihon:</strong> {}<br>'
            '<strong>Status:</strong> {}',
            obj.attempt.student.first_name,
            obj.attempt.student.last_name,
            obj.attempt.exam.title,
            obj.attempt.get_status_display()
        )
    get_attempt_info.short_description = 'Urinish Ma\'lumotlari'

    def get_mentor_info(self, obj):
        """Mentor haqida ma\'lumot"""
        return format_html(
            '<strong>Ism:</strong> {} {}<br>'
            '<strong>Username:</strong> {}<br>'
            '<strong>Email:</strong> {}',
            obj.mentor.first_name,
            obj.mentor.last_name,
            obj.mentor.username,
            obj.mentor.email
        )
    get_mentor_info.short_description = 'Mentor Ma\'lumotlari'

    def get_scores_breakdown(self, obj):
        """Barcha balllarni ko\'rsatadi"""
        return format_html(
            '<strong>Vazifani Bajarish:</strong> {}<br>'
            '<strong>Ketma-ketlik va Bog\'lanish:</strong> {}<br>'
            '<strong>Lug\'at Manbalari:</strong> {}<br>'
            '<strong>Grammatik Diapazon:</strong> {}<br>'
            '<strong>Umumiy Ball:</strong> <span style="color: #228B22; font-weight: bold;">{} / 9.0</span>',
            obj.task_achievement or '-',
            obj.coherence_cohesion or '-',
            obj.lexical_resource or '-',
            obj.grammatical_range or '-',
            obj.overall_score
        )
    get_scores_breakdown.short_description = 'Balllar Tafsili'
