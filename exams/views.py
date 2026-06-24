import json
from decimal import Decimal

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from .models import (
    Test, TestSection, Question, Choice,
    TestAttempt, Answer, CandidateProfile
)
from .forms import CandidateLoginForm


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def candidate_login(request):
    """Login page styled like the AP EAPCET candidate login screen."""
    if request.user.is_authenticated:
        return redirect('test_list')

    form = CandidateLoginForm(request.POST or None)
    error = None

    if request.method == 'POST' and form.is_valid():
        candidate_id = form.cleaned_data['candidate_id'].strip()
        password = form.cleaned_data['password']

        user = authenticate(request, username=candidate_id, password=password)
        if user is not None:
            # Check if user has a CandidateProfile - only then allow login
            try:
                candidate_profile = user.candidate_profile
                login(request, user)
                return redirect('test_list')
            except CandidateProfile.DoesNotExist:
                # User exists but no profile - reject login
                error = "Enter correct login details"
        else:
            error = "Enter correct login details"

    return render(request, 'exams/login.html', {
        'form': form,
        'error': error,
        'system_name': 'C001',
    })


def candidate_logout(request):
    logout(request)
    return redirect('login')


# ---------------------------------------------------------------------------
# Test list (dashboard after login)
# ---------------------------------------------------------------------------

@login_required
def test_list(request):
    tests = Test.objects.filter(is_active=True)
    # Show candidate's past attempts too, so they can view past results
    attempts = TestAttempt.objects.filter(candidate=request.user).select_related('test')
    return render(request, 'exams/test_list.html', {
        'tests': tests,
        'attempts': attempts,
    })


# ---------------------------------------------------------------------------
# Instructions page -> start attempt
# ---------------------------------------------------------------------------

@login_required
def test_instructions(request, test_id):
    test = get_object_or_404(Test, id=test_id, is_active=True)
    return render(request, 'exams/instructions.html', {'test': test})


@login_required
def start_test(request, test_id):
    test = get_object_or_404(Test, id=test_id, is_active=True)

    # Reuse an in-progress attempt if one exists, else create a new one
    attempt = TestAttempt.objects.filter(
        candidate=request.user, test=test, status='IN_PROGRESS'
    ).first()

    if attempt is None:
        attempt = TestAttempt.objects.create(candidate=request.user, test=test)
        # Pre-create Answer rows (status NOT_VISITED) for every question
        questions = Question.objects.filter(section__test=test)
        Answer.objects.bulk_create([
            Answer(attempt=attempt, question=q, status='NOT_VISITED')
            for q in questions
        ])

    return redirect('take_test', attempt_id=attempt.id)


# ---------------------------------------------------------------------------
# Main exam-taking interface
# ---------------------------------------------------------------------------

@login_required
def take_test(request, attempt_id):
    attempt = get_object_or_404(TestAttempt, id=attempt_id, candidate=request.user)

    if attempt.status != 'IN_PROGRESS':
        return redirect('result', attempt_id=attempt.id)

    if attempt.time_left_seconds <= 0:
        _finalize_attempt(attempt, auto=True)
        return redirect('result', attempt_id=attempt.id)

    test = attempt.test
    sections = test.sections.select_related('subject').prefetch_related('questions__choices')

    # Safe profile access - handle case where profile doesn't exist
    try:
        candidate_profile = request.user.candidate_profile
    except CandidateProfile.DoesNotExist:
        candidate_profile = None

    return render(request, 'exams/take_test.html', {
        'attempt': attempt,
        'test': test,
        'sections': sections,
        'time_left_seconds': attempt.time_left_seconds,
        'candidate_profile': candidate_profile,
    })


@login_required
def get_question_data(request, attempt_id, question_id):
    """AJAX: fetch a single question's data + the candidate's current answer status."""
    attempt = get_object_or_404(TestAttempt, id=attempt_id, candidate=request.user)
    question = get_object_or_404(Question, id=question_id, section__test=attempt.test)
    answer, _ = Answer.objects.get_or_create(attempt=attempt, question=question)

    if answer.status == 'NOT_VISITED':
        answer.status = 'NOT_ANSWERED'
        answer.save(update_fields=['status'])

    choices = [{'id': c.id, 'text': c.text} for c in question.choices.all()]

    return JsonResponse({
        'question_id': question.id,
        'order': question.order,
        'text': question.text,
        'choices': choices,
        'selected_choice_id': answer.selected_choice_id,
        'status': answer.status,
    })


@login_required
@require_POST
def save_answer(request, attempt_id):
    """AJAX: save/update an answer. action = 'save' | 'clear' | 'mark_review' | 'save_and_mark'"""
    attempt = get_object_or_404(TestAttempt, id=attempt_id, candidate=request.user)
    if attempt.status != 'IN_PROGRESS':
        return HttpResponseForbidden("Attempt already submitted.")

    data = json.loads(request.body)
    question_id = data.get('question_id')
    choice_id = data.get('choice_id')
    action = data.get('action', 'save')

    question = get_object_or_404(Question, id=question_id, section__test=attempt.test)
    answer, _ = Answer.objects.get_or_create(attempt=attempt, question=question)

    if action == 'clear':
        answer.selected_choice = None
        answer.status = 'NOT_ANSWERED'
    elif action == 'mark_review':
        if choice_id:
            answer.selected_choice = get_object_or_404(Choice, id=choice_id, question=question)
            answer.status = 'ANSWERED_MARKED'
        else:
            answer.selected_choice = None
            answer.status = 'MARKED_FOR_REVIEW'
    else:  # 'save'
        if choice_id:
            answer.selected_choice = get_object_or_404(Choice, id=choice_id, question=question)
            answer.status = 'ANSWERED'
        else:
            answer.selected_choice = None
            answer.status = 'NOT_ANSWERED'

    answer.save()

    # Return updated palette summary so the UI can refresh counts
    return JsonResponse({'ok': True, 'status': answer.status})


@login_required
def palette_status(request, attempt_id):
    """AJAX: full palette data for all questions (used to refresh the sidebar grid)."""
    attempt = get_object_or_404(TestAttempt, id=attempt_id, candidate=request.user)
    answers = Answer.objects.filter(attempt=attempt).select_related('question', 'question__section')

    data = {}
    for ans in answers:
        sec_id = ans.question.section_id
        data.setdefault(sec_id, []).append({
            'question_id': ans.question_id,
            'order': ans.question.order,
            'status': ans.status,
        })

    for sec_id in data:
        data[sec_id].sort(key=lambda x: x['order'])

    return JsonResponse({'sections': data, 'time_left_seconds': attempt.time_left_seconds})


# ---------------------------------------------------------------------------
# Submit
# ---------------------------------------------------------------------------

def _finalize_attempt(attempt, auto=False):
    """Grade the attempt and mark it submitted."""
    answers = Answer.objects.filter(attempt=attempt).select_related('question', 'selected_choice')

    total_marks = Decimal('0')
    score = Decimal('0')
    correct = wrong = unanswered = 0

    for ans in answers:
        q = ans.question
        total_marks += q.marks
        if ans.selected_choice is None:
            unanswered += 1
            continue
        if ans.selected_choice.is_correct:
            score += q.marks
            correct += 1
        else:
            score -= q.negative_marks
            wrong += 1

    attempt.score = score
    attempt.total_marks = total_marks
    attempt.correct_count = correct
    attempt.wrong_count = wrong
    attempt.unanswered_count = unanswered
    attempt.status = 'AUTO_SUBMITTED' if auto else 'SUBMITTED'
    attempt.submitted_at = timezone.now()
    attempt.save()


@login_required
@require_POST
def submit_test(request, attempt_id):
    attempt = get_object_or_404(TestAttempt, id=attempt_id, candidate=request.user)
    if attempt.status == 'IN_PROGRESS':
        _finalize_attempt(attempt, auto=False)
    return redirect('result', attempt_id=attempt.id)


@login_required
def auto_submit_test(request, attempt_id):
    """Called by JS when the timer hits zero."""
    attempt = get_object_or_404(TestAttempt, id=attempt_id, candidate=request.user)
    if attempt.status == 'IN_PROGRESS':
        _finalize_attempt(attempt, auto=True)
    return JsonResponse({'ok': True, 'redirect': f'/result/{attempt.id}/'})


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

@login_required
def result(request, attempt_id):
    attempt = get_object_or_404(TestAttempt, id=attempt_id, candidate=request.user)
    if attempt.status == 'IN_PROGRESS':
        return redirect('take_test', attempt_id=attempt.id)

    section_breakdown = []
    for section in attempt.test.sections.select_related('subject'):
        answers = Answer.objects.filter(attempt=attempt, question__section=section).select_related('selected_choice')
        correct = sum(1 for a in answers if a.selected_choice and a.selected_choice.is_correct)
        wrong = sum(1 for a in answers if a.selected_choice and not a.selected_choice.is_correct)
        unanswered = sum(1 for a in answers if not a.selected_choice)
        section_breakdown.append({
            'subject': section.subject.name,
            'correct': correct,
            'wrong': wrong,
            'unanswered': unanswered,
            'total': answers.count(),
        })

    return render(request, 'exams/result.html', {
        'attempt': attempt,
        'section_breakdown': section_breakdown,
    })
