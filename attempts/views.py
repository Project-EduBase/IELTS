from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required 
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count, Avg, Q, F, ExpressionWrapper, FloatField
from django.db import models
import json
from .models import Attempt, Review, AttemptAudio
from exams.models import Exam, ReadingSubQuestion
from groups.models import Group, GroupStudent
from django.contrib.auth.models import User

@login_required
def submit_attempt(request, exam_id):
    """Talabaning test javoblarini yuborish"""
    try:
        if request.method != 'POST':
            return JsonResponse({'error': 'POST method talab qilinadi'}, status=405)

        exam = get_object_or_404(Exam, id=exam_id)

        if not hasattr(request.user, 'profile') or request.user.profile.role != 'student':
            return JsonResponse({'error': 'Faqat talabalar test topshira oladi'}, status=403)

        # Talabaning guruhini olish
        try:
            student_group = GroupStudent.objects.get(student=request.user).group
        except GroupStudent.DoesNotExist:
            student_group = None

        # Urinish yaratish yoki olish
        attempt, created = Attempt.objects.get_or_create(
            exam=exam,
            student=request.user,
            defaults={
                'group': student_group,
                'status': 'submitted',
                'submitted_at': timezone.now(),
            }
        )

        if not created and attempt.status != 'in_progress':
            return JsonResponse({'error': 'Test allaqachon topshirilgan'}, status=400)

        # Matn javoblarini olish
        answers = {}
        for key in request.POST.keys():
            norm_key = key[:-2] if key.endswith('[]') else key

            # q_... (reading/listening), part_... (speaking), task_... (writing)
            if norm_key.startswith(('q_', 'part_', 'task_')):
                values = request.POST.getlist(key)
                answers[norm_key] = values if len(values) > 1 else values[0]

        attempt.answers = answers

        # Audio fayllarni saqlash
        for key, file in request.FILES.items():
            if key.endswith('_audio'):
                try:
                    part_id = int(key.split('_')[-2])
                    
                    audio_obj, created = AttemptAudio.objects.get_or_create(
                        attempt=attempt,
                        part_id=part_id,
                        defaults={'audio_file': file}
                    )
                    
                    if not created:
                        audio_obj.audio_file = file
                        audio_obj.save()
                        
                except (ValueError, IndexError):
                    continue

        # Status va vaqtni yangilash
        attempt.status = 'submitted'
        attempt.submitted_at = timezone.now()

        # Reading/Listening uchun avtomatik baholash
        if exam.section_type in ['reading', 'listening']:
            score, correct, incorrect = calculate_auto_score(exam, answers)

            if exam.section_type == 'reading':
                attempt.reading_score = score
            else:
                attempt.listening_score = score

            attempt.total_score = score
            attempt.correct_count = correct
            attempt.incorrect_count = incorrect
            attempt.status = 'completed'
            attempt.completed_at = timezone.now()

        attempt.save()

        return JsonResponse({
            'success': True,
            'message': 'Javoblar muvaffaqiyatli yuborildi!',
            'redirect_url': f'/exams/{exam_id}/'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Server xatosi: {str(e)}'
        }, status=500)

def normalize_answer(ans):
    """Javoblarni solishtirish uchun normalizatsiya qilish"""
    if not ans:
        return ""
    
    # Ro'yxat javoblarini qayta ishlash
    if isinstance(ans, list):
        ans = ans[0] if ans else ""
    
    # Matnga aylantirish va normalizatsiya
    ans = str(ans).strip().lower()
    
    # Harfdan keyingi nuqta va boshqa belgilarni olib tashlash
    if ans and ans[0].isalpha():
        return ans[0]
    
    return ans

def calculate_auto_score(exam, answers):
    """Reading/Listening testlari uchun avtomatik baholash"""
    correct_count = 0
    total_questions = 0

    if exam.section_type == 'reading':
        # Reading testlarini hisoblash
        for passage in exam.reading_passages.all():
            for question in passage.questions.all():
                for subq in question.subquestions.all():
                    total_questions += 1
                    question_key = f"q_{subq.id}"
                    if question_key in answers:
                        student_answer = normalize_answer(answers[question_key])
                        correct_answer = normalize_answer(subq.correct_answer)

                        if student_answer == correct_answer:
                            correct_count += 1
        
        # IELTS Reading ballar jadvali
        ielts_reading_bands = {
            40: 9.0, 39: 9.0, 38: 8.5, 37: 8.5, 36: 8.0, 35: 8.0,
            34: 7.5, 33: 7.5, 32: 7.0, 31: 7.0, 30: 7.0, 29: 6.5,
            28: 6.5, 27: 6.0, 26: 6.0, 25: 6.0, 24: 5.5, 23: 5.5,
            22: 5.0, 21: 5.0, 20: 5.0, 19: 4.5, 18: 4.5, 17: 4.0,
            16: 4.0, 15: 4.0, 14: 3.5, 13: 3.5, 12: 3.0, 11: 3.0,
            10: 3.0, 9: 2.5, 8: 2.5, 7: 2.0, 6: 2.0, 5: 2.0,
            4: 1.5, 3: 1.5, 2: 1.0, 1: 1.0, 0: 1.0
        }
        band_score = ielts_reading_bands.get(correct_count, 1.0)

    elif exam.section_type == 'listening':
        # Listening testlarini hisoblash
        for audio in exam.listening_audios.all():
            for question in audio.questions.all():
                for subq in question.subquestions.all():
                    total_questions += 1
                    question_key = f"q_{subq.id}"
                    if question_key in answers:
                        student_answer = normalize_answer(answers[question_key])
                        correct_answer = normalize_answer(subq.correct_answer)

                        if student_answer == correct_answer:
                            correct_count += 1
        
        # IELTS Listening ballar jadvali
        ielts_listening_bands = {
            40: 9.0, 39: 9.0, 38: 8.5, 37: 8.5, 36: 8.0, 35: 8.0,
            34: 7.5, 33: 7.5, 32: 7.0, 31: 7.0, 30: 6.5, 29: 6.5,
            28: 6.0, 27: 6.0, 26: 5.5, 25: 5.5, 24: 5.0, 23: 5.0,
            22: 4.5, 21: 4.5, 20: 4.0, 19: 4.0, 18: 3.5, 17: 3.5,
            16: 3.0, 15: 3.0, 14: 2.5, 13: 2.5, 12: 2.0, 11: 2.0,
            10: 1.5, 9: 1.5, 8: 1.0, 7: 1.0, 6: 1.0, 5: 1.0,
            4: 1.0, 3: 1.0, 2: 1.0, 1: 1.0, 0: 1.0
        }
        band_score = ielts_listening_bands.get(correct_count, 1.0)
    else:
        band_score = 0.0

    incorrect_count = total_questions - correct_count
    return band_score, correct_count, incorrect_count

@login_required
def review_attempt(request, attempt_id):
    """Mentor uchun testni baholash sahifasi"""
    attempt = get_object_or_404(Attempt, id=attempt_id)

    if not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor':
        messages.error(request, 'Faqat mentorlar baholash qila oladi.')
        return redirect('exams:exam_list')

    # Javoblarni olish
    answers = attempt.answers or {}

    # Audio fayllar
    audio_files = {}
    if attempt.exam.section_type == 'speaking':
        for audio in attempt.audio_files.all():
            audio_files[audio.part_id] = audio.audio_file

    # Writing vazifalari + talaba javoblari
    writing_tasks = []
    if attempt.exam.section_type == "writing":
        for task in attempt.exam.writing_tasks.all():
            answer = answers.get(f"task_{task.id}", None)
            writing_tasks.append({
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "image": task.image,
                "task_type": task.get_task_type_display(),
                "student_answer": answer,
            })

    # Ballar diapazoni
    band_scores = [i * 0.5 for i in range(19)]

    # POST so'rovida baholash
    if request.method == 'POST':
        task_achievement = float(request.POST.get('task_achievement', 0))
        coherence_cohesion = float(request.POST.get('coherence_cohesion', 0))
        lexical_resource = float(request.POST.get('lexical_resource', 0))
        grammatical_range = float(request.POST.get('grammatical_range', 0))

        overall_score = (task_achievement + coherence_cohesion +
                         lexical_resource + grammatical_range) / 4

        review, created = Review.objects.get_or_create(
            attempt=attempt,
            mentor=request.user,
            defaults={
                'task_achievement': task_achievement,
                'coherence_cohesion': coherence_cohesion,
                'lexical_resource': lexical_resource,
                'grammatical_range': grammatical_range,
                'overall_score': overall_score,
                'feedback': request.POST.get('feedback', ''),
                'strengths': request.POST.get('strengths', ''),
                'improvements': request.POST.get('improvements', ''),
            }
        )

        if not created:
            review.task_achievement = task_achievement
            review.coherence_cohesion = coherence_cohesion
            review.lexical_resource = lexical_resource
            review.grammatical_range = grammatical_range
            review.overall_score = overall_score
            review.feedback = request.POST.get('feedback', '')
            review.strengths = request.POST.get('strengths', '')
            review.improvements = request.POST.get('improvements', '')
            review.save()

        attempt.total_score = overall_score
        attempt.status = 'completed'
        attempt.completed_at = timezone.now()
        attempt.save()

        messages.success(request, 'Baholash muvaffaqiyatli saqlandi!')
        return redirect('attempts:pending_reviews')

    context = {
        "attempt": attempt,
        "answers": answers,
        "audio_files": audio_files,
        "band_scores": band_scores,
        "writing_tasks": writing_tasks,
    }

    return render(request, "attempts/review_attempt.html", context)

@login_required
def my_attempts(request):
    """Talaba uchun o'z urinishlarini ko'rish sahifasi"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'student':
        messages.error(request, 'Faqat talabalar o\'z urinishlarini ko\'ra oladi.')
        return redirect('exams:exam_list')
    
    # Talabaning barcha urinishlari
    attempts = Attempt.objects.filter(student=request.user).select_related(
        'exam', 'group'
    ).order_by('-created_at')
    
    # Statistikani hisoblash
    total_attempts = attempts.count()
    completed_attempts = attempts.filter(status='completed').count()
    
    # O'rtacha ball
    completed_with_scores = attempts.filter(status='completed', total_score__isnull=False)
    if completed_with_scores.exists():
        avg_score = round(sum(a.total_score for a in completed_with_scores) / completed_with_scores.count(), 1)
    else:
        avg_score = 0
    
    # Muvaffaqiyat darajasi
    if total_attempts > 0:
        success_rate = round((completed_attempts / total_attempts) * 100)
    else:
        success_rate = 0
    
    # Bo'limlar bo'yicha progress
    section_progress = []
    sections = [
        ('reading', 'Reading'),
        ('listening', 'Listening'), 
        ('writing', 'Writing'),
        ('speaking', 'Speaking')
    ]
    
    for section_type, section_name in sections:
        section_attempts = attempts.filter(exam__section_type=section_type)
        total_count = section_attempts.count()
        completed_count = section_attempts.filter(status='completed').count()
        
        if total_count > 0:
            percentage = round((completed_count / total_count) * 100)
            # Bo'lim bo'yicha o'rtacha ball
            section_completed = section_attempts.filter(status='completed', total_score__isnull=False)
            if section_completed.exists():
                section_avg = round(sum(a.total_score for a in section_completed) / section_completed.count(), 1)
            else:
                section_avg = 0
        else:
            percentage = 0
            section_avg = 0
        
        if total_count > 0:
            section_progress.append({
                'section_type': section_type,
                'section_name': section_name,
                'total_count': total_count,
                'completed_count': completed_count,
                'percentage': percentage,
                'avg_score': section_avg,
            })
    
    context = {
        'attempts': attempts,
        'total_attempts': total_attempts,
        'completed_attempts': completed_attempts,
        'avg_score': avg_score,
        'success_rate': success_rate,
        'section_progress': section_progress,
    }
    
    return render(request, 'attempts/my_attempts.html', context)

@login_required
def pending_reviews(request):
    """Mentor uchun baholash kutayotgan urinishlar sahifasi"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor':
        messages.error(request, 'Faqat mentorlar baholash qila oladi.')
        return redirect('exams:exam_list')
    
    # Baholash kutayotgan urinishlar (writing va speaking)
    pending_attempts = Attempt.objects.filter(
        status='submitted',
        exam__section_type__in=['writing', 'speaking'],
        group__mentor=request.user
    ).select_related('student', 'exam', 'group').order_by('-submitted_at')
    
    # Statistik ma'lumotlar
    stats = {
        'total_pending': pending_attempts.count(),
        'writing_count': pending_attempts.filter(exam__section_type='writing').count(),
        'speaking_count': pending_attempts.filter(exam__section_type='speaking').count(),
    }
    
    context = {
        'pending_attempts': pending_attempts,
        'stats': stats,
    }
    
    return render(request, 'attempts/pending_reviews.html', context)

@login_required
def mentor_stats(request):
    """Mentor uchun batafsil statistika sahifasi"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor':
        messages.error(request, 'Faqat mentorlar bu sahifani ko\'ra oladi.')
        return redirect('exams:exam_list')

    # Mentorning guruhlari
    groups = Group.objects.filter(mentor=request.user).prefetch_related('students')
    
    # Guruhlar va ularning talabalari
    groups_with_students = []
    total_students_count = 0
    total_attempts_count = 0
    
    for group in groups:
        group_students = group.students.all()
        total_students_count += group_students.count()
        
        # Guruhdagi har bir talaba uchun statistikalar
        students_data = []
        for group_student in group_students:
            student = group_student.student
            # Talabaning barcha urinishlari
            student_attempts = Attempt.objects.filter(
                student=student, 
                group=group
            ).select_related('exam')
            
            # Talaba statistikasi
            total_attempts = student_attempts.count()
            completed_attempts = student_attempts.filter(status='completed').count()
            
            # O'rtacha ball
            completed_with_scores = student_attempts.filter(
                status='completed', 
                total_score__isnull=False
            )
            if completed_with_scores.exists():
                avg_score = round(
                    sum(a.total_score for a in completed_with_scores) / completed_with_scores.count(), 
                    1
                )
            else:
                avg_score = 0
                
            total_attempts_count += total_attempts
            
            # Progress foizi
            progress_percentage = 0
            if total_attempts > 0:
                progress_percentage = round((completed_attempts / total_attempts) * 100)
            
            students_data.append({
                'student': student,
                'total_attempts': total_attempts,
                'completed_attempts': completed_attempts,
                'avg_score': avg_score,
                'progress_percentage': progress_percentage,
                'attempts': student_attempts[:5]  # Oxirgi 5 ta urinish
            })
        
        groups_with_students.append({
            'group': group,
            'students': students_data,
            'students_count': len(students_data)
        })

    # Bo'limlar bo'yicha progress (barcha talabalar uchun)
    section_progress = []
    sections = [
        ('reading', 'Reading'),
        ('listening', 'Listening'), 
        ('writing', 'Writing'),
        ('speaking', 'Speaking')
    ]
    
    for section_type, section_name in sections:
        # Guruhlardagi barcha talabalarning urinishlari
        section_attempts = Attempt.objects.filter(
            group__mentor=request.user,
            exam__section_type=section_type
        )
        
        total_count = section_attempts.count()
        completed_count = section_attempts.filter(status='completed').count()
        
        if total_count > 0:
            percentage = round((completed_count / total_count) * 100)
            # O'rtacha ball
            completed_with_scores = section_attempts.filter(
                status='completed', 
                total_score__isnull=False
            )
            if completed_with_scores.exists():
                section_avg = round(
                    sum(a.total_score for a in completed_with_scores) / completed_with_scores.count(), 
                    1
                )
            else:
                section_avg = 0
        else:
            percentage = 0
            section_avg = 0

        # Har bir bo'limda nechta talaba ishlagan
        unique_students = section_attempts.values('student').distinct().count()
        
        section_progress.append({
            'section_type': section_type,
            'section_name': section_name,
            'total_count': total_count,
            'completed_count': completed_count,
            'percentage': percentage,
            'avg_score': section_avg,
            'unique_students': unique_students,
            'total_students': total_students_count
        })

    # Baholash kutayotgan urinishlar
    pending_reviews_count = Attempt.objects.filter(
        status='submitted',
        exam__section_type__in=['writing', 'speaking'],
        group__mentor=request.user
    ).count()

    # Umumiy o'rtacha ball
    all_completed_attempts = Attempt.objects.filter(
        group__mentor=request.user,
        status='completed',
        total_score__isnull=False
    )
    if all_completed_attempts.exists():
        overall_avg_score = round(
            sum(a.total_score for a in all_completed_attempts) / all_completed_attempts.count(), 
            1
        )
    else:
        overall_avg_score = 0

    # Qo'shimcha statistikalar
    additional_stats = {
        'active_students': Attempt.objects.filter(
            group__mentor=request.user
        ).values('student').distinct().count(),
        'total_groups': groups.count(),
        'avg_attempts_per_student': round(total_attempts_count / max(total_students_count, 1), 1),
    }

    context = {
        'groups_with_students': groups_with_students,
        'total_students': total_students_count,
        'total_attempts': total_attempts_count,
        'overall_avg_score': overall_avg_score,
        'section_progress': section_progress,
        'pending_reviews_count': pending_reviews_count,
        'additional_stats': additional_stats,
    }

    return render(request, 'attempts/mentor_stats.html', context)

@login_required
def mentor_student_stats(request, student_id):
    """Mentor uchun ma'lum talabaning batafsil statistikasi"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor':
        messages.error(request, 'Faqat mentorlar bu sahifani ko\'ra oladi.')
        return redirect('exams:exam_list')

    # Talaba mentorning guruhlaridan birida ekanligini tekshirish
    student = get_object_or_404(
        User, 
        id=student_id, 
        student_group__group__mentor=request.user
    )

    # Talabaning barcha urinishlari
    attempts = Attempt.objects.filter(
        student=student,
        group__mentor=request.user
    ).select_related('exam', 'group').order_by('-created_at')

    # Asosiy statistikalar
    total_attempts = attempts.count()
    completed_attempts = attempts.filter(status='completed').count()
    in_progress_attempts = attempts.filter(status='in_progress').count()
    submitted_attempts = attempts.filter(status='submitted').count()

    # O'rtacha ball
    completed_with_scores = attempts.filter(status='completed', total_score__isnull=False)
    if completed_with_scores.exists():
        avg_score = round(
            sum(a.total_score for a in completed_with_scores) / completed_with_scores.count(), 
            1
        )
        best_score = max(a.total_score for a in completed_with_scores)
        worst_score = min(a.total_score for a in completed_with_scores)
    else:
        avg_score = 0
        best_score = 0
        worst_score = 0

    # Muvaffaqiyat darajasi
    if total_attempts > 0:
        success_rate = round((completed_attempts / total_attempts) * 100)
    else:
        success_rate = 0

    # Bo'limlar bo'yicha progress
    section_progress = []
    sections = [
        ('reading', 'Reading'),
        ('listening', 'Listening'), 
        ('writing', 'Writing'),
        ('speaking', 'Speaking')
    ]

    for section_type, section_name in sections:
        section_attempts = attempts.filter(exam__section_type=section_type)
        total_count = section_attempts.count()
        completed_count = section_attempts.filter(status='completed').count()
        
        if total_count > 0:
            percentage = round((completed_count / total_count) * 100)
            # Bo'lim bo'yicha o'rtacha ball
            section_completed = section_attempts.filter(status='completed', total_score__isnull=False)
            if section_completed.exists():
                section_avg = round(sum(a.total_score for a in section_completed) / section_completed.count(), 1)
                section_best = max(a.total_score for a in section_completed)
            else:
                section_avg = 0
                section_best = 0
        else:
            percentage = 0
            section_avg = 0
            section_best = 0

        section_progress.append({
            'section_type': section_type,
            'section_name': section_name,
            'total_count': total_count,
            'completed_count': completed_count,
            'percentage': percentage,
            'avg_score': section_avg,
            'best_score': section_best,
        })

    # Oxirgi faoliyat
    recent_activity = attempts[:10]

    # Progress grafigi uchun ma'lumotlar
    progress_data = []
    for attempt in attempts.filter(status='completed', total_score__isnull=False).order_by('completed_at')[:10]:
        progress_data.append({
            'date': attempt.completed_at.strftime('%d.%m'),
            'score': attempt.total_score,
            'exam': attempt.exam.title,
        })

    context = {
        'student': student,
        'attempts': attempts,
        'total_attempts': total_attempts,
        'completed_attempts': completed_attempts,
        'in_progress_attempts': in_progress_attempts,
        'submitted_attempts': submitted_attempts,
        'avg_score': avg_score,
        'best_score': best_score,
        'worst_score': worst_score,
        'success_rate': success_rate,
        'section_progress': section_progress,
        'recent_activity': recent_activity,
        'progress_data': progress_data,
    }

    return render(request, 'attempts/mentor_student_stats.html', context)

@login_required
def attempt_result(request, attempt_id):
    """Test natijalarini ko'rsatish sahifasi"""
    attempt = get_object_or_404(Attempt, id=attempt_id)
    
    # Faqat talaba o'zining natijalarini ko'ra oladi yoki mentor
    if request.user != attempt.student and (not hasattr(request.user, 'profile') or request.user.profile.role != 'mentor'):
        messages.error(request, 'Siz bu natijalarni ko\'ra olmaysiz.')
        return redirect('exams:exam_list')
    
    answers = []
    
    # JSON maydonidan javoblarni yuklash
    if attempt.answers:
        answers_dict = attempt.answers
        # Javoblarni template uchun kerakli formatga o'tkazish
        for question_id, given_answer in answers_dict.items():
            # 'q_' prefiksini olib tashlash
            real_id = question_id.replace('q_', '') if question_id.startswith('q_') else question_id
            try:
                question = ReadingSubQuestion.objects.get(id=real_id)
                # Ro'yxat va matn javoblarini qayta ishlash
                if isinstance(given_answer, list):
                    given_answer_text = ', '.join(str(x) for x in given_answer)
                else:
                    given_answer_text = str(given_answer)

                # Solishtirish uchun normalizatsiya
                normalized_student_answer = normalize_answer(given_answer)
                normalized_correct_answer = normalize_answer(question.correct_answer)
                
                # Ko'rsatish uchun asl formatni saqlash
                display_answer = given_answer_text.strip()
                
                answers.append({
                    'question': question,
                    'given_answer': display_answer,
                    'is_correct': normalized_student_answer == normalized_correct_answer
                })
            except ReadingSubQuestion.DoesNotExist:
                continue
    
    # Muvaffaqiyat foizini hisoblash
    success_percentage = 0
    if answers:
        correct_answers = sum(1 for answer in answers if answer['is_correct'])
        success_percentage = round((correct_answers / len(answers)) * 100)

    context = {
        'attempt': attempt,
        'answers': answers,
        'correct_count': attempt.correct_count or 0,
        'incorrect_count': attempt.incorrect_count or 0,
        'success_percentage': success_percentage,
        'attempt_time': attempt.duration_minutes if hasattr(attempt, 'duration_minutes') else 0,
    }
    
    return render(request, "attempts/attempt_detail.html", context)

# Qo'shimcha yordamchi funksiyalar
def get_student_progress_stats(student):
    """Talabaning progress statistikasini olish"""
    attempts = Attempt.objects.filter(student=student)
    
    stats = {
        'total_attempts': attempts.count(),
        'completed_attempts': attempts.filter(status='completed').count(),
        'avg_score': 0,
        'section_breakdown': {},
    }
    
    # O'rtacha ball
    completed_with_scores = attempts.filter(status='completed', total_score__isnull=False)
    if completed_with_scores.exists():
        stats['avg_score'] = round(
            sum(a.total_score for a in completed_with_scores) / completed_with_scores.count(), 
            1
        )
    
    # Bo'limlar bo'yicha tahlil
    for section in ['reading', 'listening', 'writing', 'speaking']:
        section_attempts = attempts.filter(exam__section_type=section)
        section_completed = section_attempts.filter(status='completed')
        
        stats['section_breakdown'][section] = {
            'total': section_attempts.count(),
            'completed': section_completed.count(),
            'avg_score': 0,
        }
        
        if section_completed.exists():
            stats['section_breakdown'][section]['avg_score'] = round(
                sum(a.total_score for a in section_completed) / section_completed.count(), 
                1
            )
    
    return stats

def get_group_stats(group):
    """Guruh statistikasini olish"""
    students = group.students.all()
    attempts = Attempt.objects.filter(group=group)
    
    stats = {
        'total_students': students.count(),
        'active_students': attempts.values('student').distinct().count(),
        'total_attempts': attempts.count(),
        'completed_attempts': attempts.filter(status='completed').count(),
        'avg_score': 0,
    }
    
    # O'rtacha ball
    completed_with_scores = attempts.filter(status='completed', total_score__isnull=False)
    if completed_with_scores.exists():
        stats['avg_score'] = round(
            sum(a.total_score for a in completed_with_scores) / completed_with_scores.count(), 
            1
        )
    
    return stats