from django.urls import path, include
from rest_framework.routers import DefaultRouter
from hostel.views import (
    # Page views
    index_view, login_view, signup_view, forgot_password_view, verify_email_view,
    student_dashboard_view, admin_dashboard_view,
    # Auth APIs
    RegisterAPIView, LoginAPIView, UserDetailsAPIView, ForgotPasswordAPIView, VerifyEmailAPIView,
    # Dashboard APIs
    StudentDashboardAPIView, AdminDashboardAPIView,
    # ViewSets
    ApplicationViewSet, HostelBlockViewSet, RoomViewSet, RoomChangeRequestViewSet,
    ComplaintViewSet, FeedbackViewSet, AnnouncementViewSet, PaymentViewSet,
    # Action APIs
    ChatbotAPIView, ExportReportsAPIView
)

router = DefaultRouter()
router.register(r'applications', ApplicationViewSet, basename='application')
router.register(r'blocks', HostelBlockViewSet, basename='block')
router.register(r'rooms', RoomViewSet, basename='room')
router.register(r'change-requests', RoomChangeRequestViewSet, basename='change-request')
router.register(r'complaints', ComplaintViewSet, basename='complaint')
router.register(r'feedback', FeedbackViewSet, basename='feedback')
router.register(r'announcements', AnnouncementViewSet, basename='announcement')
router.register(r'payments', PaymentViewSet, basename='payment')

urlpatterns = [
    # Pages
    path('', index_view, name='index'),
    path('login/', login_view, name='page_login'),
    path('signup/', signup_view, name='page_signup'),
    path('forgot-password/', forgot_password_view, name='page_forgot_password'),
    path('verify-email/', verify_email_view, name='page_verify_email'),
    path('dashboard/', student_dashboard_view, name='page_student_dashboard'),
    path('admin-dashboard/', admin_dashboard_view, name='page_admin_dashboard'),
    
    # API endpoints
    path('api/', include(router.urls)),
    path('api/auth/register/', RegisterAPIView.as_view(), name='api_register'),
    path('api/auth/login/', LoginAPIView.as_view(), name='api_login'),
    path('api/auth/user/', UserDetailsAPIView.as_view(), name='api_user_details'),
    path('api/auth/forgot-password/', ForgotPasswordAPIView.as_view(), name='api_forgot_password'),
    path('api/auth/verify-email/', VerifyEmailAPIView.as_view(), name='api_verify_email'),
    path('api/student/dashboard/', StudentDashboardAPIView.as_view(), name='api_student_dashboard'),
    path('api/admin/dashboard/', AdminDashboardAPIView.as_view(), name='api_admin_dashboard'),
    path('api/chatbot/', ChatbotAPIView.as_view(), name='api_chatbot'),
    path('api/reports/export/', ExportReportsAPIView.as_view(), name='api_export_reports'),
]
