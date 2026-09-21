from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'university', 'major', 'is_public', 'updated_at')
    list_filter = ('is_public', 'gender', 'year')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'university', 'major', 'city')
