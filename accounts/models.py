from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    ADMIN = 'admin'
    MENTOR = 'mentor'
    STUDENT = 'student'
    
    ROLE_CHOICES = [
        (ADMIN, 'Admin'),
        (MENTOR, 'Mentor'),
        (STUDENT, 'Student'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=STUDENT, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'accounts_profile'
        verbose_name = 'Profil'
        verbose_name_plural = 'Profillar'
        indexes = [
            models.Index(fields=['role']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"
    
    def get_display_name(self):
        """Foydalanuvchining to'liq nomini qaytarish"""
        return self.user.get_full_name() or self.user.username


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Yangi User yaratilganda avtomatik Profile ham yaratiladi
    """
    if created:
        Profile.objects.get_or_create(user=instance)
