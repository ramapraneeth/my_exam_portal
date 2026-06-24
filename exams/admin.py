from django.contrib import admin
from .models import (
    Subject, Test, TestSection, Question, Choice,
    CandidateProfile, TestAttempt, Answer
)


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4
    max_num = 6


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('order', 'section', 'question_type', 'short_text', 'marks', 'negative_marks')
    list_filter = ('section__test', 'section__subject', 'question_type')
    search_fields = ('text',)
    inlines = [ChoiceInline]
    ordering = ('section', 'order')

    def short_text(self, obj):
        return obj.text[:60]
    short_text.short_description = 'Question'


class TestSectionInline(admin.TabularInline):
    model = TestSection
    extra = 1


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ('title', 'system_name', 'duration_minutes', 'is_active', 'subject_list', 'total_questions', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('title', 'system_name')
    inlines = [TestSectionInline]

    def subject_list(self, obj):
        return ", ".join(s.name for s in obj.subjects)
    subject_list.short_description = 'Subjects'


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(TestSection)
class TestSectionAdmin(admin.ModelAdmin):
    list_display = ('test', 'subject', 'order', 'question_count')
    list_filter = ('test', 'subject')


@admin.register(CandidateProfile)
class CandidateProfileAdmin(admin.ModelAdmin):
    list_display = ('candidate_id', 'user', 'photo')
    search_fields = ('candidate_id', 'user__username', 'user__first_name', 'user__last_name')


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0
    readonly_fields = ('question', 'selected_choice', 'status', 'updated_at')
    can_delete = False


@admin.register(TestAttempt)
class TestAttemptAdmin(admin.ModelAdmin):
    list_display = ('candidate', 'test', 'status', 'score', 'total_marks', 'started_at', 'submitted_at')
    list_filter = ('status', 'test')
    search_fields = ('candidate__username',)
    inlines = [AnswerInline]
    readonly_fields = ('started_at',)
