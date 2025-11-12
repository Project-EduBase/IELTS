from django import forms
from django.contrib import admin
from django.contrib.auth.models import User
from .models import Group, GroupStudent


class GroupStudentInline(admin.TabularInline):
    """Guruhdagi talabalarni ko'rsatish uchun inline admin."""
    model = GroupStudent
    extra = 0
    verbose_name = "Guruh talabasi"
    verbose_name_plural = "Guruh talabalari"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'student':
            kwargs['queryset'] = User.objects.filter(profile__role='student').order_by('first_name', 'last_name')
            # Talaba dropdownida to'liq ism va familiyani ko'rsatish
            class StudentChoiceField(forms.ModelChoiceField):
                def label_from_instance(self, obj):
                    return f"{obj.get_full_name() or obj.username} ({obj.username})"
            kwargs['form_class'] = StudentChoiceField
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class GroupAdminForm(forms.ModelForm):
    """Guruh admini uchun maxsus forma, o'qituvchi dropdownida to'liq ismlarni ko'rsatadi."""
    class Meta:
        model = Group
        fields = '__all__'
        labels = {
            'name': 'Guruh nomi',
            'mentor': "O'qituvchi",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # O'qituvchi dropdownida to'liq ismlarni ko'rsatish
        self.fields['mentor'].queryset = User.objects.filter(profile__role='mentor').order_by('first_name', 'last_name')
        self.fields['mentor'].label_from_instance = lambda obj: f"{obj.get_full_name() or obj.username} ({obj.username})"


class GroupStudentAdminForm(forms.ModelForm):
    """Guruh talabasi admini uchun maxsus forma, talaba dropdownida to'liq ismlarni ko'rsatadi."""
    class Meta:
        model = GroupStudent
        fields = '__all__'
        labels = {
            'group': 'Guruh',
            'student': 'Talaba',
            'joined_at': "Qo'shilgan sana",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Talaba dropdownida to'liq ism va familiyani ko'rsatish
        self.fields['student'].queryset = User.objects.filter(profile__role='student').order_by('first_name', 'last_name')
        self.fields['student'].label_from_instance = lambda obj: f"{obj.get_full_name() or obj.username} ({obj.username})"


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    """Guruh modeli uchun admin sozlamalari."""
    form = GroupAdminForm
    list_display = ['nomi', 'murabbiy', 'talabalar_soni', 'yaratilgan_sana']
    list_filter = ['created_at']
    search_fields = ['name', 'mentor__username', 'mentor__first_name', 'mentor__last_name']
    inlines = [GroupStudentInline]

    def nomi(self, obj):
        """Guruh nomini ko'rsatish."""
        return obj.name
    nomi.short_description = "Guruh nomi"

    def murabbiy(self, obj):
        """O'qituvchi ismini ko'rsatish."""
        return obj.mentor.get_full_name() or obj.mentor.username
    murabbiy.short_description = "O'qituvchi"

    def talabalar_soni(self, obj):
        """Guruhdagi talabalar sonini ko'rsatish."""
        return obj.students.count()
    talabalar_soni.short_description = "Talabalar soni"

    def yaratilgan_sana(self, obj):
        """Guruh yaratilgan sanani ko'rsatish."""
        return obj.created_at
    yaratilgan_sana.short_description = "Yaratilgan sana"


@admin.register(GroupStudent)
class GroupStudentAdmin(admin.ModelAdmin):
    """Guruh talabasi modeli uchun admin sozlamalari."""
    form = GroupStudentAdminForm
    list_display = ['talaba', 'guruh', 'qoshilgan_sana']
    list_filter = ['group', 'joined_at']
    search_fields = ['student__username', 'student__first_name', 'student__last_name', 'group__name']

    def talaba(self, obj):
        """Talaba ism va familiyasini ko'rsatish."""
        return obj.student.get_full_name() or obj.student.username
    talaba.short_description = "Talaba"

    def guruh(self, obj):
        """Guruh nomini ko'rsatish."""
        return obj.group.name
    guruh.short_description = "Guruh"

    def qoshilgan_sana(self, obj):
        """Talaba guruhga qo'shilgan sanani ko'rsatish."""
        return obj.joined_at
    qoshilgan_sana.short_description = "Qo'shilgan sana"
