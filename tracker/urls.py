from django.urls import path
from . import views
from .views import (
    SignUpView, LoginView, COD_DashboardView, Exam_DashboardView, Lecturer_DashboardView, LogoutView, StudentSelectView, 
    MissingMarkSelectView, COD_NominalRollListView, COD_ResultListView, COD_LoadResultView, COD_LoadNominalRollView,
    Exam_NominalRollListView, Exam_ResultListView, Exam_LoadResultView, Exam_LoadNominalRollView, NominalRollListView,
    ResultListView, LoadResultView, LoadNominalRollView, CodComplaintsView, AssignLecturerView, CodRespondView,
    LecturerComplaintsListView, LecturerRespondView, CODResponseListView, CODApproveResponseView,
    ExamRespondView, ExamComplaintsListView , DeleteResponseConfirmationView, ExamOfficerApprovedResponsesView  
)

urlpatterns = [
    path('student/', StudentSelectView.as_view(), name='student'),
    path('post/complaints/', MissingMarkSelectView.as_view(), name='post-complaint'),
    path('register/',SignUpView.as_view(), name='signup'),
    path('login/',LoginView.as_view(), name='login'),
    
    path('lecturer-dashboard/',Lecturer_DashboardView.as_view(), name='lecturer-dashboard'),
    path('exam-dashboard/',Exam_DashboardView.as_view(), name='exam-dashboard'),
    path('cod-dashboard/',COD_DashboardView.as_view(), name='cod-dashboard'),
    
    path('logout/', LogoutView.as_view(), name='logout'),
    
    path('cod/load-nominal-roll/', COD_LoadNominalRollView.as_view(), name='cod-load-nominal-roll'),
    path('cod/load-result/', COD_LoadResultView.as_view(), name='cod-load-result'),

    path('cod/nominal-roll/', COD_NominalRollListView.as_view(), name='cod-nominal-roll'),
    path('cod/result/', COD_ResultListView.as_view(), name='cod-result'),
    
    path('exam/load-nominal-roll/', Exam_LoadNominalRollView.as_view(), name='exam-load-nominal-roll'),
    path('exam/load-result/', Exam_LoadResultView.as_view(), name='exam-load-result'),
    
    path('exam/nominal-roll/', Exam_NominalRollListView.as_view(), name='exam-nominal-roll'),
    path('exam/result/', Exam_ResultListView.as_view(), name='exam-result'),

    path('load-nominal-roll/', LoadNominalRollView.as_view(), name='load-nominal-roll'),
    path('load-result/', LoadResultView.as_view(), name='load-result'),

    path('nominal-roll/', NominalRollListView.as_view(), name='nominal-roll'),
    path('result/', ResultListView.as_view(), name='result'),
    
    path('cod/complaints/', CodComplaintsView.as_view(), name='cod-complaints'),
    path('cod/complaints/<str:complaint_code>/assign/', AssignLecturerView.as_view(), name='assign-lecturer'),
    path('cod/complaints/<str:complaint_code>/respond/', CodRespondView.as_view(), name='cod-respond'),
    
    path('lecturer/complaints/', LecturerComplaintsListView.as_view(), name='lecturer-complaints'),
    path('lecturer/complaint/<str:complaint_code>/respond/', LecturerRespondView.as_view(), name='lecturer-respond-to-complaint'),
    
    path('exam/complaints/', ExamComplaintsListView.as_view(), name='exam-complaints'),
    path('exam/complaint/<str:complaint_code>/respond/', ExamRespondView.as_view(), name='exam-respond-to-complaint'),
    
    path('responses/', CODResponseListView.as_view(), name='cod_responses_list'),
    path('approve-response/<str:complaint_code>/', CODApproveResponseView.as_view(), name='cod_approve_response'),
    
    path('approved-responses/', ExamOfficerApprovedResponsesView.as_view(), name='approved-responses'),
    path('delete-response/<int:response_id>/', DeleteResponseConfirmationView.as_view(), name='delete-response-confirmation'),
]
