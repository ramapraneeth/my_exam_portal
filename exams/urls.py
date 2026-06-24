from django.urls import path
from . import views

urlpatterns = [
    path('', views.candidate_login, name='login'),
    path('logout/', views.candidate_logout, name='logout'),

    path('tests/', views.test_list, name='test_list'),
    path('test/<int:test_id>/instructions/', views.test_instructions, name='test_instructions'),
    path('test/<int:test_id>/start/', views.start_test, name='start_test'),

    path('attempt/<int:attempt_id>/', views.take_test, name='take_test'),
    path('attempt/<int:attempt_id>/question/<int:question_id>/', views.get_question_data, name='get_question_data'),
    path('attempt/<int:attempt_id>/save-answer/', views.save_answer, name='save_answer'),
    path('attempt/<int:attempt_id>/palette/', views.palette_status, name='palette_status'),
    path('attempt/<int:attempt_id>/submit/', views.submit_test, name='submit_test'),
    path('attempt/<int:attempt_id>/auto-submit/', views.auto_submit_test, name='auto_submit_test'),

    path('result/<int:attempt_id>/', views.result, name='result'),
]
