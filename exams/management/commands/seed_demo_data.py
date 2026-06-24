"""
Management command to seed demo data: a candidate login, plus one
single-subject test and one multi-subject (EAPCET-style) test with
sample questions, so you can try the whole flow immediately.

Run with: python manage.py seed_demo_data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from exams.models import Subject, Test, TestSection, Question, Choice, CandidateProfile


class Command(BaseCommand):
    help = "Seed the database with demo subjects, tests, questions, and a candidate login."

    def handle(self, *args, **options):
        # --- Candidate user ---
        user, created = User.objects.get_or_create(
            username='11111',
            defaults={'first_name': 'John', 'last_name': 'Smith'}
        )
        if created:
            user.set_password('pass123')
            user.save()
            CandidateProfile.objects.create(user=user, candidate_id='11111')
            self.stdout.write(self.style.SUCCESS("Created candidate login -> ID: 11111 / Password: pass123"))
        else:
            self.stdout.write("Candidate 11111 already exists.")

        # --- Subjects ---
        maths, _ = Subject.objects.get_or_create(name='Mathematics')
        physics, _ = Subject.objects.get_or_create(name='Physics')
        chemistry, _ = Subject.objects.get_or_create(name='Chemistry')

        # --- Single-subject test: Mathematics only ---
        math_test, created = Test.objects.get_or_create(
            title='Mathematics Mock Test 1',
            defaults={'system_name': 'C001', 'duration_minutes': 30,
                      'instructions': 'This is a Mathematics-only mock test.'}
        )
        if created:
            section = TestSection.objects.create(test=math_test, subject=maths, order=1)
            self._add_sample_questions(section, count=5)
            self.stdout.write(self.style.SUCCESS("Created single-subject test: Mathematics Mock Test 1"))

        # --- Multi-subject test: EAMCET-style ---
        full_test, created = Test.objects.get_or_create(
            title='EAMCET Engineering Stream - Full Mock',
            defaults={'system_name': 'C001', 'duration_minutes': 180,
                      'instructions': 'This test contains Mathematics, Physics, and Chemistry sections.'}
        )
        if created:
            sec_m = TestSection.objects.create(test=full_test, subject=maths, order=1)
            sec_p = TestSection.objects.create(test=full_test, subject=physics, order=2)
            sec_c = TestSection.objects.create(test=full_test, subject=chemistry, order=3)
            self._add_sample_questions(sec_m, count=5)
            self._add_sample_questions(sec_p, count=5)
            self._add_sample_questions(sec_c, count=5)
            self.stdout.write(self.style.SUCCESS("Created multi-subject test: EAMCET Engineering Stream - Full Mock"))

        self.stdout.write(self.style.SUCCESS("\nDone! Login at / with Candidate ID 11111 / Password pass123"))

    def _add_sample_questions(self, section, count=5):
        for i in range(1, count + 1):
            q = Question.objects.create(
                section=section,
                text=f"Sample question {i} for {section.subject.name}. "
                     f"(Replace this with your real question text via the admin panel.)",
                order=i,
                marks=1,
                negative_marks=0.33,
            )
            options = ['Option A', 'Option B', 'Option C', 'Option D']
            for idx, opt in enumerate(options):
                Choice.objects.create(
                    question=q,
                    text=f"{opt} for Q{i}",
                    is_correct=(idx == 0),  # first option correct, just for demo
                    order=idx,
                )
