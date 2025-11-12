from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Profile
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect
from django.urls import reverse


class CustomUserCreationForm(UserCreationForm):
    """Maxsus foydalanuvchi yaratish formasi, ism va familiyani so'raydi."""

    first_name = forms.CharField(label="Ism", required=True)
    last_name = forms.CharField(label="Familiya", required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["first_name", "last_name", "username", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Foydalanuvchi nomi"
        self.fields["password1"].label = "Parol"
        self.fields["password2"].label = "Parolni tasdiqlash"


class ProfileInlineForm(forms.ModelForm):
    """Profil inline formasi, role ni tanlash uchun."""

    class Meta:
        model = Profile
        fields = ["role"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].label = "Rol"
        self.fields["role"].required = True  # Role tanlash majburiy


class ProfileInline(admin.StackedInline):
    """Foydalanuvchi profilini admin panelida ko'rsatish uchun inline."""

    model = Profile
    form = ProfileInlineForm
    can_delete = False
    verbose_name = "Profil"
    verbose_name_plural = "Profillar"

    def get_formset(self, request, obj=None, **kwargs):
        """Yangi foydalanuvchi yaratilganda role ni dastlabki qiymat bilan to'ldirish."""
        formset = super().get_formset(request, obj, **kwargs)
        if obj is None:  # Yangi foydalanuvchi yaratilayotganda
            if request.path.startswith("/admin/accounts/adminuser/"):
                formset.form.base_fields["role"].initial = "admin"
            elif request.path.startswith("/admin/accounts/mentoruser/"):
                formset.form.base_fields["role"].initial = "mentor"
            elif request.path.startswith("/admin/accounts/studentuser/"):
                formset.form.base_fields["role"].initial = "student"
        return formset


class AdminUserForm(forms.ModelForm):
    """Admin foydalanuvchilari uchun maxsus forma, to'liq ismlarni ko'rsatadi."""

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "username",
            "email",
            "is_active",
            "is_staff",
            "is_superuser",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].label = "Ism"
        self.fields["last_name"].label = "Familiya"
        self.fields["username"].label = "Foydalanuvchi nomi"
        self.fields["email"].label = "Elektron pochta"
        self.fields["is_active"].label = "Faol"
        self.fields["is_staff"].label = "Xodim"
        self.fields["is_superuser"].label = "Super foydalanuvchi"


class MentorUserForm(forms.ModelForm):
    """O'qituvchi foydalanuvchilari uchun maxsus forma, to'liq ismlarni ko'rsatadi."""

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].label = "Ism"
        self.fields["last_name"].label = "Familiya"
        self.fields["username"].label = "Foydalanuvchi nomi"
        self.fields["email"].label = "Elektron pochta"
        self.fields["is_active"].label = "Faol"


class StudentUserForm(forms.ModelForm):
    """Talaba foydalanuvchilari uchun maxsus forma, to'liq ismlarni ko'rsatadi."""

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].label = "Ism"
        self.fields["last_name"].label = "Familiya"
        self.fields["username"].label = "Foydalanuvchi nomi"
        self.fields["email"].label = "Elektron pochta"
        self.fields["is_active"].label = "Faol"


class AdminUser(User):
    """Proxy model for users with 'admin' role."""

    class Meta:
        proxy = True
        verbose_name = "Admin"
        verbose_name_plural = "Adminlar"


class MentorUser(User):
    """Proxy model for users with 'mentor' role."""

    class Meta:
        proxy = True
        verbose_name = "O'qituvchi"
        verbose_name_plural = "O'qituvchilar"


class StudentUser(User):
    """Proxy model for users with 'student' role."""

    class Meta:
        proxy = True
        verbose_name = "Talaba"
        verbose_name_plural = "Talabalar"


@admin.register(AdminUser)
class AdminUserAdmin(BaseUserAdmin):
    """Admin panelida faqat admin rolli foydalanuvchilarni ko'rsatish."""

    form = AdminUserForm
    add_form = CustomUserCreationForm
    inlines = [ProfileInline]
    list_display = [
        "ism_familiya",
        "foydalanuvchi_nomi",
        "elektron_pochta",
        "faol",
        "xodim",
        "super_foydalanuvchi",
    ]
    list_filter = ["is_active", "is_staff", "is_superuser"]
    search_fields = ["first_name", "last_name", "username", "email"]
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "first_name",
                    "last_name",
                    "username",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    def get_queryset(self, request):
        """Faqat admin rolli foydalanuvchilarni qaytarish."""
        return User.objects.filter(profile__role="admin")

    def save_model(self, request, obj, form, change):
        """Foydalanuvchi saqlanganda Profile role ni to'g'ri o'rnatish"""
        if not change:
            super().save_model(request, obj, form, change)
            profile, created = Profile.objects.get_or_create(user=obj)
            profile.role = "admin"
            profile.save()
        else:
            super().save_model(request, obj, form, change)
            if hasattr(obj, "profile"):
                obj.profile.role = "admin"
                obj.profile.save()

    def response_add(self, request, obj, post_url_continue=None):
        """Yangi user yaratilgandan keyin list page'ga redirect qilish"""
        return HttpResponseRedirect(reverse("admin:accounts_adminuser_changelist"))

    def get_object(self, request, object_id, from_field=None):
        """Obyektni to'g'ri yuklash uchun."""
        queryset = self.get_queryset(request)
        return super().get_object(request, object_id, from_field)

    def ism_familiya(self, obj):
        """Foydalanuvchi ism va familiyasini ko'rsatish."""
        return obj.get_full_name() or obj.username

    ism_familiya.short_description = "Ism va familiya"

    def foydalanuvchi_nomi(self, obj):
        """Foydalanuvchi nomini ko'rsatish."""
        return obj.username

    foydalanuvchi_nomi.short_description = "Foydalanuvchi nomi"

    def elektron_pochta(self, obj):
        """Elektron pochtani ko'rsatish."""
        return obj.email

    elektron_pochta.short_description = "Elektron pochta"

    def faol(self, obj):
        """Foydalanuvchi faol holatini ko'rsatish."""
        return obj.is_active

    faol.short_description = "Faol"
    faol.boolean = True

    def xodim(self, obj):
        """Foydalanuvchi xodim holatini ko'rsatish."""
        return obj.is_staff

    xodim.short_description = "Xodim"
    xodim.boolean = True

    def super_foydalanuvchi(self, obj):
        """Foydalanuvchi super foydalanuvchi holatini ko'rsatish."""
        return obj.is_superuser

    super_foydalanuvchi.short_description = "Super foydalanuvchi"
    super_foydalanuvchi.boolean = True


@admin.register(MentorUser)
class MentorUserAdmin(BaseUserAdmin):
    """Admin panelida faqat o'qituvchi rolli foydalanuvchilarni ko'rsatish."""

    form = MentorUserForm
    add_form = CustomUserCreationForm
    inlines = [ProfileInline]
    list_display = ["ism_familiya", "foydalanuvchi_nomi", "elektron_pochta", "faol"]
    list_filter = ["is_active"]
    search_fields = ["first_name", "last_name", "username", "email"]
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "first_name",
                    "last_name",
                    "username",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    def get_queryset(self, request):
        """Faqat o'qituvchi rolli foydalanuvchilarni qaytarish."""
        return User.objects.filter(profile__role="mentor")

    def save_model(self, request, obj, form, change):
        """Foydalanuvchi saqlanganda Profile role ni to'g'ri o'rnatish"""
        if not change:
            super().save_model(request, obj, form, change)
            profile, created = Profile.objects.get_or_create(user=obj)
            profile.role = "mentor"
            profile.save()
        else:
            super().save_model(request, obj, form, change)
            if hasattr(obj, "profile"):
                obj.profile.role = "mentor"
                obj.profile.save()

    def response_add(self, request, obj, post_url_continue=None):
        """Yangi user yaratilgandan keyin list page'ga redirect qilish"""
        return HttpResponseRedirect(reverse("admin:accounts_mentoruser_changelist"))

    def get_object(self, request, object_id, from_field=None):
        """Obyektni to'g'ri yuklash uchun."""
        queryset = self.get_queryset(request)
        return super().get_object(request, object_id, from_field)

    def ism_familiya(self, obj):
        """O'qituvchi ism va familiyasini ko'rsatish."""
        return obj.get_full_name() or obj.username

    ism_familiya.short_description = "Ism va familiya"

    def foydalanuvchi_nomi(self, obj):
        """Foydalanuvchi nomini ko'rsatish."""
        return obj.username

    foydalanuvchi_nomi.short_description = "Foydalanuvchi nomi"

    def elektron_pochta(self, obj):
        """Elektron pochtani ko'rsatish."""
        return obj.email

    elektron_pochta.short_description = "Elektron pochta"

    def faol(self, obj):
        """Foydalanuvchi faol holatini ko'rsatish."""
        return obj.is_active

    faol.short_description = "Faol"
    faol.boolean = True


@admin.register(StudentUser)
class StudentUserAdmin(BaseUserAdmin):
    """Admin panelida faqat talaba rolli foydalanuvchilarni ko'rsatish."""

    form = StudentUserForm
    add_form = CustomUserCreationForm
    inlines = [ProfileInline]
    list_display = ["ism_familiya", "foydalanuvchi_nomi", "elektron_pochta", "faol"]
    list_filter = ["is_active"]
    search_fields = ["first_name", "last_name", "username", "email"]
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "first_name",
                    "last_name",
                    "username",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    def get_queryset(self, request):
        """Faqat talaba rolli foydalanuvchilarni qaytarish."""
        return User.objects.filter(profile__role="student")

    def save_model(self, request, obj, form, change):
        """Foydalanuvchi saqlanganda Profile role ni to'g'ri o'rnatish"""
        if not change:
            super().save_model(request, obj, form, change)
            profile, created = Profile.objects.get_or_create(user=obj)
            profile.role = "student"
            profile.save()
        else:
            super().save_model(request, obj, form, change)
            if hasattr(obj, "profile"):
                obj.profile.role = "student"
                obj.profile.save()

    def response_add(self, request, obj, post_url_continue=None):
        """Yangi user yaratilgandan keyin list page'ga redirect qilish"""
        return HttpResponseRedirect(reverse("admin:accounts_studentuser_changelist"))

    def get_object(self, request, object_id, from_field=None):
        """Obyektni to'g'ri yuklash uchun."""
        queryset = self.get_queryset(request)
        return super().get_object(request, object_id, from_field)

    def ism_familiya(self, obj):
        """Talaba ism va familiyasini ko'rsatish."""
        return obj.get_full_name() or obj.username

    ism_familiya.short_description = "Ism va familiya"

    def foydalanuvchi_nomi(self, obj):
        """Foydalanuvchi nomini ko'rsatish."""
        return obj.username

    foydalanuvchi_nomi.short_description = "Foydalanuvchi nomi"

    def elektron_pochta(self, obj):
        """Elektron pochtani ko'rsatish."""
        return obj.email

    elektron_pochta.short_description = "Elektron pochta"

    def faol(self, obj):
        """Foydalanuvchi faol holatini ko'rsatish."""
        return obj.is_active

    faol.short_description = "Faol"
    faol.boolean = True


# Unregister the default User admin and keep only the custom ones
admin.site.unregister(User)
admin.site.unregister(Group)
