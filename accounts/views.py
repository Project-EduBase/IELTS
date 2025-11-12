from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Avg, Q
from django.views.decorators.http import require_http_methods
from groups.models import Group, GroupStudent
from attempts.models import Attempt
from exams.models import ExamAssignment

@require_http_methods(["GET", "POST"])
def user_login(request):
    """Foydalanuvchi login qilish"""
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        # Validatsiya
        if not username or not password:
            messages.error(request, "Username va parol kiritish majburiy!")
            return render(request, 'accounts/login.html')
        
        # Authentifikatsiya
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('accounts:dashboard')
        else:
            messages.error(request, "Username yoki parol noto'g'ri!")
    
    return render(request, 'accounts/login.html')

def user_logout(request):
    """Foydalanuvchini logout qilish"""
    logout(request)
    return redirect('accounts:login')


@login_required
def dashboard(request):
    """Foydalanuvchi roliga qarab dashboard ga redirect qilish"""
    role = getattr(request.user.profile, 'role', 'student')
    
    redirect_map = {
        'admin': '/admin/',
        'mentor': 'accounts:mentor_dashboard',
        'student': 'accounts:student_dashboard'
    }
    
    return redirect(redirect_map.get(role, 'accounts:student_dashboard'))

@login_required
def mentor_dashboard(request):
    """O'qituvchi dashboard"""
    if request.user.profile.role != 'mentor':
        return redirect('accounts:dashboard')
    
    # Optimallashtirish: select_related
    mentor_groups = Group.objects.filter(
        mentor=request.user
    ).select_related('mentor')
    
    # Statistika
    total_students = GroupStudent.objects.filter(
        group__in=mentor_groups
    ).count()
    
    pending_reviews = Attempt.objects.filter(
        group__in=mentor_groups,
        status='submitted',
        exam__section_type__in=['writing', 'speaking']
    ).count()
    
    recent_attempts = Attempt.objects.filter(
        group__in=mentor_groups
    ).select_related('student', 'exam', 'group').order_by('-created_at')[:5]
    
    context = {
        'mentor_groups': mentor_groups,
        'total_students': total_students,
        'pending_reviews': pending_reviews,
        'recent_attempts': recent_attempts,
    }
    
    return render(request, 'accounts/mentor_dashboard.html', context)

@login_required
def student_dashboard(request):
    """Talaba dashboard - tezkor yuklanish uchun optimized"""
    if request.user.profile.role != 'student':
        return redirect('accounts:dashboard')
    
    # Talaba gruppasini olish (optimized - select_related)
    student_group_obj = GroupStudent.objects.select_related(
        'group', 'group__mentor'
    ).filter(student=request.user).first()
    
    student_group = student_group_obj.group if student_group_obj else None
    
    # Imtihonlar - qarab group bo'lsa yoki hammada bo'lsa (prefetch qilish)
    if student_group:
        available_exams = ExamAssignment.objects.filter(
            Q(group=student_group) | Q(all_groups=True)
        ).select_related('exam').order_by('-exam__created_at')[:3]
    else:
        available_exams = ExamAssignment.objects.filter(
            all_groups=True
        ).select_related('exam').order_by('-exam__created_at')[:3]
    
    # Talabaning harakat ta'rixi (select_related bilan optimized)
    attempts = Attempt.objects.filter(
        student=request.user
    ).select_related('exam').order_by('-created_at')
    
    # Statistika - bitta aggregate query
    attempts_stats = attempts.aggregate(
        total=Count('id'),
        completed=Count('id', filter=Q(status='completed')),
        avg_score=Avg('total_score', filter=Q(status='completed', total_score__isnull=False))
    )
    
    # Ma'lumotlar
    recent_attempts = list(attempts[:3])
    available_exams_list = list(available_exams)
    available_exams_total = ExamAssignment.objects.filter(
        Q(group=student_group) | Q(all_groups=True) if student_group else Q(all_groups=True)
    ).count()
    
    student_attempts_total = Attempt.objects.filter(student=request.user).count()
    
    context = {
        'student_group': student_group,
        'available_exams': available_exams_list,
        'available_exams_count': available_exams_total,
        'student_attempts': recent_attempts,
        'student_attempts_count': student_attempts_total,
        'total_attempts': attempts_stats['total'],
        'completed_attempts': attempts_stats['completed'],
        'avg_score': round(attempts_stats['avg_score'] or 0, 1),
    }
    
    return render(request, 'accounts/student_dashboard.html', context)