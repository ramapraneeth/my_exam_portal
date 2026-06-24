"""
Management command to check and fix database consistency issues.
Run with: python manage.py fix_database_issues
"""
from django.core.management.base import BaseCommand
from django.db.models import Count
from exams.models import User, CandidateProfile, TestAttempt, Answer, Question


class Command(BaseCommand):
    help = 'Check and fix database consistency issues in the exam portal'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Actually fix the issues found (default is dry-run)',
        )

    def handle(self, *args, **options):
        fix_mode = options.get('fix', False)
        mode_str = "FIX MODE" if fix_mode else "DRY-RUN MODE"
        self.stdout.write(self.style.SUCCESS(f'\n=== Database Check ({mode_str}) ===\n'))

        # 1. Check for users without CandidateProfile
        self.check_missing_profiles(fix_mode)

        # 2. Check for orphaned attempts (no questions for the test)
        self.check_orphaned_attempts(fix_mode)

        # 3. Check for orphaned answers (questions that don't exist)
        self.check_orphaned_answers(fix_mode)

        # 4. Check for attempts with incomplete answers
        self.check_incomplete_answers(fix_mode)

        self.stdout.write(self.style.SUCCESS('\n=== Database Check Complete ===\n'))

    def check_missing_profiles(self, fix_mode):
        """Find users without CandidateProfile."""
        self.stdout.write(self.style.HTTP_INFO('\n1. Checking for users without CandidateProfile...'))
        
        users_without_profile = User.objects.filter(
            candidate_profile__isnull=True
        ).exclude(is_superuser=True, is_staff=True)

        if users_without_profile.exists():
            count = users_without_profile.count()
            self.stdout.write(
                self.style.WARNING(f'   Found {count} user(s) without CandidateProfile:')
            )
            for user in users_without_profile:
                self.stdout.write(f'   - {user.username} (ID: {user.id})')
            
            if fix_mode:
                for user in users_without_profile:
                    CandidateProfile.objects.create(
                        user=user,
                        candidate_id=f"{user.id}_{user.username}"
                    )
                self.stdout.write(self.style.SUCCESS(f'   ✓ Created CandidateProfile for {count} user(s)'))
        else:
            self.stdout.write(self.style.SUCCESS('   ✓ All users have CandidateProfile'))

    def check_orphaned_attempts(self, fix_mode):
        """Find attempts where the test has no questions."""
        self.stdout.write(self.style.HTTP_INFO('\n2. Checking for orphaned attempts...'))
        
        attempts_with_no_questions = []
        for attempt in TestAttempt.objects.select_related('test'):
            question_count = Question.objects.filter(section__test=attempt.test).count()
            if question_count == 0:
                attempts_with_no_questions.append(attempt)

        if attempts_with_no_questions:
            count = len(attempts_with_no_questions)
            self.stdout.write(
                self.style.WARNING(f'   Found {count} attempt(s) for tests with no questions:')
            )
            for attempt in attempts_with_no_questions:
                self.stdout.write(
                    f'   - Attempt {attempt.id} ({attempt.candidate.username} - {attempt.test.title})'
                )
            
            if fix_mode:
                for attempt in attempts_with_no_questions:
                    Answer.objects.filter(attempt=attempt).delete()
                    attempt.delete()
                self.stdout.write(self.style.SUCCESS(f'   ✓ Deleted {count} orphaned attempt(s)'))
        else:
            self.stdout.write(self.style.SUCCESS('   ✓ No orphaned attempts found'))

    def check_orphaned_answers(self, fix_mode):
        """Find answers referencing deleted questions."""
        self.stdout.write(self.style.HTTP_INFO('\n3. Checking for orphaned answers...'))
        
        orphaned_answers = Answer.objects.filter(question__isnull=True)
        
        if orphaned_answers.exists():
            count = orphaned_answers.count()
            self.stdout.write(self.style.WARNING(f'   Found {count} orphaned answer(s)'))
            
            if fix_mode:
                orphaned_answers.delete()
                self.stdout.write(self.style.SUCCESS(f'   ✓ Deleted {count} orphaned answer(s)'))
        else:
            self.stdout.write(self.style.SUCCESS('   ✓ No orphaned answers found'))

    def check_incomplete_answers(self, fix_mode):
        """Find attempts that don't have answers for all questions."""
        self.stdout.write(self.style.HTTP_INFO('\n4. Checking for incomplete answers...'))
        
        incomplete_count = 0
        for attempt in TestAttempt.objects.select_related('test'):
            questions = Question.objects.filter(section__test=attempt.test)
            answers = Answer.objects.filter(attempt=attempt)
            
            if questions.count() != answers.count():
                self.stdout.write(
                    self.style.WARNING(
                        f'   - Attempt {attempt.id}: {answers.count()} answers, {questions.count()} questions'
                    )
                )
                
                if fix_mode:
                    # Create missing answers
                    existing_question_ids = set(
                        answers.values_list('question_id', flat=True)
                    )
                    missing_questions = questions.exclude(id__in=existing_question_ids)
                    
                    Answer.objects.bulk_create([
                        Answer(attempt=attempt, question=q, status='NOT_VISITED')
                        for q in missing_questions
                    ])
                    incomplete_count += 1

        if incomplete_count > 0:
            self.stdout.write(self.style.SUCCESS(f'   ✓ Fixed {incomplete_count} attempt(s)'))
        else:
            if fix_mode:
                self.stdout.write(self.style.SUCCESS('   ✓ All attempts have complete answers'))
            else:
                self.stdout.write(self.style.SUCCESS('   ✓ All attempts have complete answers'))
