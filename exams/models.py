"""
Data model for the mock test / exam portal.

Design notes:
- A Test can have ONE or MANY subjects (e.g. a single-subject Maths test,
  or a full EAPCET-style test with Maths + Physics + Chemistry).
  This is handled by TestSection, which links a Test to a Subject.
  A Test with one TestSection = single-subject test.
  A Test with three TestSections = multi-subject test like the screenshot.
- Answer.status drives the colored question-palette grid seen in the
  exam UI (Answered / Not Answered / Not Visited / Marked for Review /
  Answered & Marked for Review).
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator


class Subject(models.Model):
    """E.g. Mathematics, Physics, Chemistry."""
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Test(models.Model):
    """A mock test / exam, e.g. 'EAMCET Engineering Stream - Full Mock 1'."""
    title = models.CharField(max_length=255)
    system_name = models.CharField(
        max_length=50, default='C001',
        help_text="Short code shown top-left on login screen, e.g. C001"
    )
    duration_minutes = models.PositiveIntegerField(
        default=180, validators=[MinValueValidator(1)],
        help_text="Total test duration in minutes"
    )
    instructions = models.TextField(
        blank=True,
        help_text="Shown on the instructions page before the test starts"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def subjects(self):
        return Subject.objects.filter(testsection__test=self).distinct()

    @property
    def total_questions(self):
        return Question.objects.filter(section__test=self).count()


class TestSection(models.Model):
    """
    Links a Test to a Subject. A Test having 1 row here = single subject test.
    A Test having 3 rows here (Maths/Physics/Chem) = multi-subject test.
    """
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='sections')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0, help_text="Tab order, left to right")

    class Meta:
        ordering = ['order']
        unique_together = ('test', 'subject')

    def __str__(self):
        return f"{self.test.title} - {self.subject.name}"

    @property
    def question_count(self):
        return self.questions.count()


class Question(models.Model):
    QUESTION_TYPES = [
        ('MCQ', 'Multiple Choice (Single Answer)'),
    ]

    section = models.ForeignKey(TestSection, on_delete=models.CASCADE, related_name='questions')
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPES, default='MCQ')
    text = models.TextField(help_text="Question text. Supports plain text or HTML for formulas/images.")
    order = models.PositiveIntegerField(default=0, help_text="Question number within the section")
    marks = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    negative_marks = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.0,
        help_text="Marks deducted for a wrong answer, e.g. 0.33"
    )

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Q{self.order}: {self.text[:50]}"


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.TextField()
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.text[:40]} ({'correct' if self.is_correct else 'wrong'})"


class CandidateProfile(models.Model):
    """Extra info per candidate, beyond Django's built-in User."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='candidate_profile')
    candidate_id = models.CharField(max_length=30, unique=True, help_text="Login ID / hall ticket number")
    photo = models.ImageField(upload_to='candidate_photos/', blank=True, null=True)

    def __str__(self):
        return f"{self.candidate_id} - {self.user.get_full_name() or self.user.username}"


class TestAttempt(models.Model):
    """One candidate's attempt at one test."""
    STATUS_CHOICES = [
        ('IN_PROGRESS', 'In Progress'),
        ('SUBMITTED', 'Submitted'),
        ('AUTO_SUBMITTED', 'Auto-submitted (time up)'),
    ]

    candidate = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attempts')
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='attempts')
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='IN_PROGRESS')

    # Cached results, filled in on submit
    score = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    total_marks = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    correct_count = models.PositiveIntegerField(default=0)
    wrong_count = models.PositiveIntegerField(default=0)
    unanswered_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.candidate.username} - {self.test.title} ({self.status})"

    @property
    def time_elapsed_seconds(self):
        from django.utils import timezone
        if self.status != 'IN_PROGRESS':
            return None
        delta = timezone.now() - self.started_at
        return int(delta.total_seconds())

    @property
    def time_left_seconds(self):
        total = self.test.duration_minutes * 60
        elapsed = self.time_elapsed_seconds or 0
        return max(0, total - elapsed)


class Answer(models.Model):
    """
    A candidate's answer/status for a single question within an attempt.
    `status` drives the colored question-palette UI.
    """
    STATUS_CHOICES = [
        ('NOT_VISITED', 'Not Visited'),
        ('NOT_ANSWERED', 'Not Answered'),
        ('ANSWERED', 'Answered'),
        ('MARKED_FOR_REVIEW', 'Marked for Review'),
        ('ANSWERED_MARKED', 'Answered & Marked for Review'),
    ]

    attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(Choice, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NOT_VISITED')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('attempt', 'question')

    def __str__(self):
        return f"{self.attempt} - Q{self.question.order} - {self.status}"

    @property
    def is_correct(self):
        if not self.selected_choice:
            return False
        return self.selected_choice.is_correct
