from django.contrib import admin

from .models import Question, QuestionOption, QuestionResponse, QuestionnaireCategory


@admin.register(QuestionnaireCategory)
class QuestionnaireCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'display_order', 'is_active')
    list_filter = ('is_active',)
    prepopulated_fields = {'slug': ('name',)}


class QuestionOptionInline(admin.TabularInline):
    model = QuestionOption
    extra = 0


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'category', 'question_type', 'order', 'is_required', 'is_active')
    list_filter = ('question_type', 'is_required', 'is_active', 'category_ref')
    search_fields = ('text',)
    inlines = (QuestionOptionInline,)


@admin.register(QuestionResponse)
class QuestionResponseAdmin(admin.ModelAdmin):
    list_display = ('user', 'question', 'value', 'created_at')
    search_fields = ('user__email', 'question__text')
    readonly_fields = ('user', 'question', 'value', 'created_at')
