import os
import re
import qrcode
from io import BytesIO
from datetime import datetime
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db import models
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

# ReportLab and Openpyxl imports for export
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import openpyxl

from hostel.models import (
    CustomUser, StudentProfile, HostelBlock, Room, RoomAllocation,
    RoomChangeRequest, Complaint, Feedback, Announcement, Payment, Notification
)
from hostel.serializers import (
    UserSerializer, StudentProfileSerializer, RegisterSerializer,
    HostelBlockSerializer, RoomSerializer, RoomAllocationSerializer,
    RoomChangeRequestSerializer, ComplaintSerializer, FeedbackSerializer,
    AnnouncementSerializer, PaymentSerializer, NotificationSerializer
)

def generate_receipt_pdf(payment):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        textColor=colors.HexColor("#1A365D"),
        spaceAfter=15,
        alignment=1
    )
    
    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#2D3748")
    )
    
    label_style = ParagraphStyle(
        'LabelStyle',
        parent=body_style,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor("#4A5568")
    )
    
    story.append(Paragraph("CampusStay Hostel System", title_style))
    story.append(Paragraph("OFFICIAL FEE PAYMENT RECEIPT", ParagraphStyle('Sub', parent=title_style, fontSize=14, spaceAfter=20)))
    story.append(Spacer(1, 10))
    
    data = [
        [Paragraph("Transaction ID:", label_style), Paragraph(payment.transaction_id, body_style)],
        [Paragraph("Student Name:", label_style), Paragraph(payment.student.full_name, body_style)],
        [Paragraph("Student ID:", label_style), Paragraph(payment.student.student_id, body_style)],
        [Paragraph("Department:", label_style), Paragraph(payment.student.department, body_style)],
        [Paragraph("Paid Amount:", label_style), Paragraph(f"₹{payment.amount:.2f}", body_style)],
        [Paragraph("Payment Method:", label_style), Paragraph(payment.method, body_style)],
        [Paragraph("Payment Status:", label_style), Paragraph(payment.status, body_style)],
        [Paragraph("Payment Date:", label_style), Paragraph(str(payment.paid_at or payment.created_at), body_style)],
    ]
    
    t = Table(data, colWidths=[150, 300])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F7FAFC")),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor("#E2E8F0")),
        ('PADDING', (0,0), (-1,-1), 10),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    
    story.append(t)
    story.append(Spacer(1, 40))
    
    story.append(Paragraph("This is a computer-generated receipt and does not require a physical signature.", ParagraphStyle('Footer', parent=body_style, fontSize=8, alignment=1, textColor=colors.HexColor("#A0AEC0"))))
    
    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf

# ==========================================
# PAGE VIEWS (Serving HTML Templates)
# ==========================================

def index_view(request):
    return render(request, 'index.html')

def login_view(request):
    return render(request, 'auth/login.html')

def signup_view(request):
    return render(request, 'auth/signup.html')

def forgot_password_view(request):
    return render(request, 'auth/forgot_password.html')

def verify_email_view(request):
    return render(request, 'auth/verify_email.html')

def student_dashboard_view(request):
    return render(request, 'student/dashboard.html')

def admin_dashboard_view(request):
    return render(request, 'admin/dashboard.html')


# ==========================================
# AUTHENTICATION & REGISTRATION API
# ==========================================

class RegisterAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            profile = serializer.save()
            return Response({
                "message": "Registration successful! Please verify your email.",
                "student_id": profile.student_id
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username_or_id = request.data.get('username')
        password = request.data.get('password')
        
        try:
            profile = StudentProfile.objects.get(student_id=username_or_id)
            username = profile.user.username
        except StudentProfile.DoesNotExist:
            username = username_or_id
            
        user = authenticate(username=username, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "role": user.role,
                "username": user.username,
                "email": user.email
            }, status=status.HTTP_200_OK)
        return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

class UserDetailsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        data = serializer.data
        if request.user.role == 'STUDENT':
            try:
                profile = request.user.student_profile
                data['profile_status'] = profile.application_status
                data['student_id'] = profile.student_id
            except StudentProfile.DoesNotExist:
                data['profile_status'] = None
        return Response(data)

class ForgotPasswordAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({"email": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = CustomUser.objects.get(email=email)
            # Create a mock notification and password reset email console print
            Notification.objects.create(
                user=user,
                title="Password Reset Request Received",
                message="A request to reset your password has been received. Follow the steps sent to your email to configure a new password.",
                email_sent=True
            )
            print(f"[SMTP MOCK] Password reset link sent to: {email}")
            return Response({"message": "Password reset link sent to your registered email address."})
        except CustomUser.DoesNotExist:
            return Response({"detail": "No user found with this email address."}, status=status.HTTP_404_NOT_FOUND)

class VerifyEmailAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        student_id = request.data.get('student_id')
        code = request.data.get('code', '123456') # Default dummy code
        
        try:
            profile = StudentProfile.objects.get(student_id=student_id)
            if profile.application_status == 'PENDING':
                profile.application_status = 'UNDER_REVIEW'
                profile.save()
                
                Notification.objects.create(
                    user=profile.user,
                    title="Email Verified Successfully",
                    message="Your email has been verified. Your hostel application is now under review by the administrator.",
                    email_sent=True
                )
                return Response({"message": "Email successfully verified! Application moved to 'Under Review'."})
            return Response({"message": "Email already verified or application is past the verification stage."})
        except StudentProfile.DoesNotExist:
            return Response({"detail": "Student ID not found."}, status=status.HTTP_404_NOT_FOUND)


# ==========================================
# STUDENT DASHBOARD API
# ==========================================

class StudentDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'STUDENT':
            return Response({"detail": "Only students can view the student dashboard."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            profile = request.user.student_profile
        except StudentProfile.DoesNotExist:
            return Response({"detail": "Student profile not found."}, status=status.HTTP_404_NOT_FOUND)

        # Get room details if allocated
        allocation = RoomAllocation.objects.filter(student=profile, status='ACTIVE').first()
        room_data = None
        if allocation:
            room_data = RoomSerializer(allocation.room).data
            room_data['bed_number'] = allocation.bed_number
            
        # Get notifications
        notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:10]
        
        # Get recent payments
        payments = Payment.objects.filter(student=profile).order_by('-created_at')

        # Build timeline statuses
        timeline = [
            {"step": 1, "title": "Registration Submitted", "completed": True, "date": profile.created_at.strftime('%Y-%m-%d %H:%M')},
            {"step": 2, "title": "Under Review", "completed": profile.application_status in ['UNDER_REVIEW', 'APPROVED', 'ROOM_ALLOCATED']},
            {"step": 3, "title": "Approved", "completed": profile.application_status in ['APPROVED', 'ROOM_ALLOCATED']},
            {"step": 4, "title": "Room Allocated", "completed": profile.application_status == 'ROOM_ALLOCATED'},
            {"step": 5, "title": "Payment Pending", "completed": payments.filter(status='SUCCESSFUL').exists() or profile.application_status == 'ROOM_ALLOCATED'},
            {"step": 6, "title": "Payment Completed", "completed": payments.filter(status='SUCCESSFUL').exists()}
        ]

        return Response({
            "profile": StudentProfileSerializer(profile).data,
            "room": room_data,
            "timeline": timeline,
            "notifications": NotificationSerializer(notifications, many=True).data,
            "payments": PaymentSerializer(payments, many=True).data
        })


# ==========================================
# ADMIN DASHBOARD API
# ==========================================

class AdminDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'ADMIN':
            return Response({"detail": "Access denied. Admin role required."}, status=status.HTTP_403_FORBIDDEN)

        # Metrics
        total_students = StudentProfile.objects.count()
        pending_apps = StudentProfile.objects.filter(application_status='PENDING').count()
        under_review_apps = StudentProfile.objects.filter(application_status='UNDER_REVIEW').count()
        approved_apps = StudentProfile.objects.filter(application_status='APPROVED').count()
        allocated_apps = StudentProfile.objects.filter(application_status='ROOM_ALLOCATED').count()
        rejected_apps = StudentProfile.objects.filter(application_status='REJECTED').count()
        
        total_rooms = Room.objects.count()
        total_beds = Room.objects.aggregate(models.Sum('capacity'))['capacity__sum'] or 0
        occupied_beds = Room.objects.aggregate(models.Sum('occupied_beds'))['occupied_beds__sum'] or 0
        available_beds = max(0, total_beds - occupied_beds)

        successful_payments = Payment.objects.filter(status='SUCCESSFUL')
        total_revenue = successful_payments.aggregate(models.Sum('amount'))['amount__sum'] or 0.0

        # Registration trends (grouped by month or date)
        # For simplicity, returning the counts for the last 5 days
        trends_labels = ["Day -4", "Day -3", "Day -2", "Yesterday", "Today"]
        trends_data = [
            StudentProfile.objects.filter(created_at__date=timezone.now().date() - timezone.timedelta(days=i)).count()
            for i in reversed(range(5))
        ]

        # Occupancy by block
        occupancy_trends = []
        for block in HostelBlock.objects.all():
            rooms = block.rooms.all()
            b_total = rooms.aggregate(models.Sum('capacity'))['capacity__sum'] or 0
            b_occupied = rooms.aggregate(models.Sum('occupied_beds'))['occupied_beds__sum'] or 0
            occupancy_trends.append({
                "block": block.name,
                "capacity": b_total,
                "occupied": b_occupied
            })

        return Response({
            "metrics": {
                "total_students": total_students,
                "pending_applications": pending_apps + under_review_apps,
                "approved_applications": approved_apps,
                "allocated_rooms": allocated_apps,
                "rejected_applications": rejected_apps,
                "total_rooms": total_rooms,
                "available_beds": available_beds,
                "occupied_beds": occupied_beds,
                "total_revenue": total_revenue
            },
            "charts": {
                "registration_labels": trends_labels,
                "registration_data": trends_data,
                "occupancy_trends": occupancy_trends
            }
        })


# ==========================================
# ADMIN ACTIONS - APPLICATIONS
# ==========================================

class ApplicationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = StudentProfileSerializer
    queryset = StudentProfile.objects.all()

    def get_queryset(self):
        queryset = StudentProfile.objects.all().order_by('-created_at')
        if self.request.user.role != 'ADMIN':
            queryset = queryset.filter(user=self.request.user)
        
        # Search & Filter
        search = self.request.query_params.get('search')
        status_filter = self.request.query_params.get('status')
        gender_filter = self.request.query_params.get('gender')
        dept_filter = self.request.query_params.get('department')

        if search:
            queryset = queryset.filter(
                models.Q(full_name__icontains=search) | 
                models.Q(student_id__icontains=search)
            )
        if status_filter:
            queryset = queryset.filter(application_status=status_filter)
        if gender_filter:
            queryset = queryset.filter(gender=gender_filter)
        if dept_filter:
            queryset = queryset.filter(department__icontains=dept_filter)

        return queryset

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        if request.user.role != 'ADMIN':
            return Response({"detail": "Only admins can perform this action."}, status=status.HTTP_403_FORBIDDEN)
        
        profile = self.get_object()
        new_status = request.data.get('status')
        remarks = request.data.get('remarks', '')

        if new_status not in dict(StudentProfile.STATUS_CHOICES):
            return Response({"detail": "Invalid status option."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Update
        profile.application_status = new_status
        if new_status == 'ON_HOLD' or remarks:
            profile.additional_info_requested = remarks
        profile.save()

        # Notification
        Notification.objects.create(
            user=profile.user,
            title=f"Application Updated: {profile.get_application_status_display()}",
            message=f"Your registration application has been updated to '{profile.get_application_status_display()}'. " + 
                    (f"Admin remarks: {remarks}" if remarks else ""),
            email_sent=True
        )

        return Response({"message": f"Application status successfully changed to {new_status}."})

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        if request.user.role != 'ADMIN':
            return Response({"detail": "Only admins can perform this action."}, status=status.HTTP_403_FORBIDDEN)
        
        profile = self.get_object()
        user = profile.user
        
        if user == request.user:
            return Response({"detail": "You cannot block yourself."}, status=status.HTTP_400_BAD_REQUEST)
            
        user.is_active = not user.is_active
        user.save()
        
        status_str = "unblocked" if user.is_active else "blocked"
        return Response({"message": f"Student {profile.full_name} has been {status_str}."})

    def destroy(self, request, *args, **kwargs):
        if request.user.role != 'ADMIN':
            return Response({"detail": "Only admins can delete students."}, status=status.HTTP_403_FORBIDDEN)
        
        profile = self.get_object()
        user = profile.user
        
        if user == request.user:
            return Response({"detail": "You cannot delete yourself."}, status=status.HTTP_400_BAD_REQUEST)
            
        # Decrement occupied beds if student is currently allocated
        active_allocations = RoomAllocation.objects.filter(student=profile, status='ACTIVE')
        for alloc in active_allocations:
            room = alloc.room
            if room.occupied_beds > 0:
                room.occupied_beds -= 1
                room.save()
                
        user.delete()
        return Response({"message": "Student profile and user account deleted successfully."})


# ==========================================
# ROOM MANAGEMENT & ALLOCATION
# ==========================================

class HostelBlockViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = HostelBlockSerializer
    queryset = HostelBlock.objects.all()

class RoomViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = RoomSerializer
    queryset = Room.objects.all()

    def get_queryset(self):
        queryset = Room.objects.all()
        block_id = self.request.query_params.get('block')
        if block_id:
            queryset = queryset.filter(block_id=block_id)
        return queryset

    @action(detail=False, methods=['get'])
    def recommendations(self, request):
        if request.user.role != 'STUDENT':
            return Response({"detail": "Only students can fetch room recommendations."}, status=status.HTTP_403_FORBIDDEN)
        try:
            profile = request.user.student_profile
        except StudentProfile.DoesNotExist:
            return Response({"detail": "Student profile not found."}, status=status.HTTP_404_NOT_FOUND)

        recs = recommend_rooms(profile)
        return Response(recs)

    @action(detail=True, methods=['post'])
    def allocate(self, request, pk=None):
        if request.user.role != 'ADMIN':
            return Response({"detail": "Only admins can allocate rooms."}, status=status.HTTP_403_FORBIDDEN)
        
        room = self.get_object()
        student_id = request.data.get('student_id')
        
        student = get_object_or_404(StudentProfile, student_id=student_id)
        
        if student.application_status not in ['APPROVED', 'ROOM_ALLOCATED']:
            return Response({"detail": "Student application is not approved yet."}, status=status.HTTP_400_BAD_REQUEST)
        
        if room.available_beds <= 0:
            return Response({"detail": "No beds available in this room."}, status=status.HTTP_400_BAD_REQUEST)

        # Deallocate any previous active allocations for this student
        previous_allocations = RoomAllocation.objects.filter(student=student, status='ACTIVE')
        for old_alloc in previous_allocations:
            old_alloc.status = 'VACATED'
            old_alloc.vacated_at = timezone.now()
            old_alloc.save()
            
            # Decrement old room occupancy
            old_room = old_alloc.room
            if old_room.occupied_beds > 0:
                old_room.occupied_beds -= 1
                old_room.save()

        bed_number = request.data.get('bed_number')

        # Create new allocation
        RoomAllocation.objects.create(
            student=student,
            room=room,
            status='ACTIVE',
            bed_number=bed_number
        )

        # Increment occupied beds
        room.occupied_beds += 1
        room.save()

        # Update student application status
        student.application_status = 'ROOM_ALLOCATED'
        student.save()

        # Send notification
        Notification.objects.create(
            user=student.user,
            title="Hostel Room Allocated",
            message=f"Congratulations! You have been allocated Room {room.room_number} in {room.block.name} (Floor {room.floor_number}). Please complete your fee payment to secure your seat.",
            email_sent=True
        )

        return Response({"message": f"Successfully allocated Room {room.room_number} to {student.full_name}."})

    @action(detail=False, methods=['post'])
    def change_allocation(self, request):
        if request.user.role != 'ADMIN':
            return Response({"detail": "Only admins can change allocations."}, status=status.HTTP_403_FORBIDDEN)
            
        student_id = request.data.get('student_id')
        new_room_id = request.data.get('room_id')
        
        student = get_object_or_404(StudentProfile, student_id=student_id)
        new_room = get_object_or_404(Room, id=new_room_id)
        
        if new_room.available_beds <= 0:
            return Response({"detail": "The preferred room is fully occupied."}, status=status.HTTP_400_BAD_REQUEST)
            
        # Perform change
        previous_allocations = RoomAllocation.objects.filter(student=student, status='ACTIVE')
        for old_alloc in previous_allocations:
            old_alloc.status = 'CHANGED'
            old_alloc.vacated_at = timezone.now()
            old_alloc.save()
            
            old_room = old_alloc.room
            if old_room.occupied_beds > 0:
                old_room.occupied_beds -= 1
                old_room.save()
                
        # Create new allocation
        RoomAllocation.objects.create(
            student=student,
            room=new_room,
            status='ACTIVE'
        )
        new_room.occupied_beds += 1
        new_room.save()
        
        Notification.objects.create(
            user=student.user,
            title="Room Allocation Changed",
            message=f"Your room allocation has been updated. You have been transferred to Room {new_room.room_number} in {new_room.block.name}.",
            email_sent=True
        )
        
        return Response({"message": "Room allocation changed successfully."})

    @action(detail=False, methods=['get'])
    def verify_qr(self, request):
        student_id = request.query_params.get('student_id')
        student = get_object_or_404(StudentProfile, student_id=student_id)
        
        allocation = RoomAllocation.objects.filter(student=student, status='ACTIVE').first()
        if not allocation:
            return Response({"verified": False, "detail": "No active room allocation found."})
            
        return Response({
            "verified": True,
            "student_name": student.full_name,
            "student_id": student.student_id,
            "department": student.department,
            "year": student.year_of_study,
            "room_number": allocation.room.room_number,
            "block_name": allocation.room.block.name,
            "allocated_at": allocation.allocated_at.strftime('%Y-%m-%d')
        })

    @action(detail=False, methods=['get'])
    def qr_code(self, request):
        if request.user.role != 'STUDENT':
            return Response({"detail": "Only students can fetch their QR code."}, status=status.HTTP_403_FORBIDDEN)
        
        profile = request.user.student_profile
        # Generate QR code pointing to verification API
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        verification_data = f"http://localhost:8000/api/rooms/verify_qr/?student_id={profile.student_id}"
        qr.add_data(verification_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        import base64
        img_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        buffer.close()
        
        return Response({"qr_base64": f"data:image/png;base64,{img_b64}"})


class RoomChangeRequestViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = RoomChangeRequestSerializer
    queryset = RoomChangeRequest.objects.all()

    def get_queryset(self):
        if self.request.user.role == 'ADMIN':
            return RoomChangeRequest.objects.all().order_by('-created_at')
        return RoomChangeRequest.objects.filter(student=self.request.user.student_profile).order_by('-created_at')

    def create(self, request, *args, **kwargs):
        if request.user.role != 'STUDENT':
            return Response({"detail": "Only students can request room changes."}, status=status.HTTP_403_FORBIDDEN)
            
        student = request.user.student_profile
        current_alloc = RoomAllocation.objects.filter(student=student, status='ACTIVE').first()
        if not current_alloc:
            return Response({"detail": "You do not have an active room allocation to change."}, status=status.HTTP_400_BAD_REQUEST)
            
        # Check if already has a pending change request
        if RoomChangeRequest.objects.filter(student=student, status='PENDING').exists():
            return Response({"detail": "You already have a pending room change request."}, status=status.HTTP_400_BAD_REQUEST)
            
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(student=student, current_room=current_alloc.room)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        if request.user.role != 'ADMIN':
            return Response({"detail": "Only admins can review requests."}, status=status.HTTP_403_FORBIDDEN)
            
        change_req = self.get_object()
        new_status = request.data.get('status') # APPROVED or REJECTED
        remarks = request.data.get('remarks', '')
        
        if new_status not in ['APPROVED', 'REJECTED']:
            return Response({"detail": "Invalid status selection."}, status=status.HTTP_400_BAD_REQUEST)
            
        change_req.status = new_status
        change_req.admin_remarks = remarks
        change_req.save()
        
        if new_status == 'APPROVED':
            # Perform allocation logic automatically if possible, or leave it for administrative manual change
            Notification.objects.create(
                user=change_req.student.user,
                title="Room Change Request Approved",
                message=f"Your room change request has been APPROVED. Warden remarks: {remarks}. Please contact the office to retrieve your new key card.",
                email_sent=True
            )
        else:
            Notification.objects.create(
                user=change_req.student.user,
                title="Room Change Request Rejected",
                message=f"Your room change request has been REJECTED. Warden remarks: {remarks}.",
                email_sent=True
            )
            
        return Response({"message": f"Change request status updated to {new_status}."})


# ==========================================
# COMPLAINTS, ANNOUNCEMENTS, FEEDBACK API
# ==========================================

class ComplaintViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ComplaintSerializer
    queryset = Complaint.objects.all()

    def get_queryset(self):
        if self.request.user.role == 'ADMIN':
            return Complaint.objects.all().order_by('-created_at')
        return Complaint.objects.filter(student=self.request.user.student_profile).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(student=self.request.user.student_profile)

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        if request.user.role != 'ADMIN':
            return Response({"detail": "Only admins can update complaint status."}, status=status.HTTP_403_FORBIDDEN)
            
        complaint = self.get_object()
        new_status = request.data.get('status')
        remarks = request.data.get('remarks', '')
        
        if new_status not in dict(Complaint.STATUS_CHOICES):
            return Response({"detail": "Invalid status selection."}, status=status.HTTP_400_BAD_REQUEST)
            
        complaint.status = new_status
        complaint.admin_remarks = remarks
        complaint.save()
        
        Notification.objects.create(
            user=complaint.student.user,
            title=f"Complaint Status Update",
            message=f"Your complaint ticket #{complaint.id} is now '{complaint.get_status_display()}'. Warden comment: {remarks}",
            email_sent=True
        )
        
        return Response({"message": "Complaint status updated."})

class FeedbackViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = FeedbackSerializer
    queryset = Feedback.objects.all()

    def get_queryset(self):
        if self.request.user.role == 'ADMIN':
            return Feedback.objects.all().order_by('-created_at')
        return Feedback.objects.filter(student=self.request.user.student_profile).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(student=self.request.user.student_profile)

class AnnouncementViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = AnnouncementSerializer
    queryset = Announcement.objects.all()

    def get_queryset(self):
        queryset = Announcement.objects.all().order_by('-created_at')
        if self.request.user.role == 'STUDENT':
            queryset = queryset.filter(target_role__in=['ALL', 'STUDENT'])
        return queryset

    def perform_create(self, serializer):
        if self.request.user.role != 'ADMIN':
            raise permissions.PermissionDenied("Only admins can post announcements.")
        serializer.save(posted_by=self.request.user)


# ==========================================
# PAYMENTS API & RECEIPT GENERATION
# ==========================================

class PaymentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentSerializer
    queryset = Payment.objects.all()

    def get_queryset(self):
        if self.request.user.role == 'ADMIN' or getattr(self, 'action', None) == 'receipt':
            return Payment.objects.all().order_by('-created_at')
        return Payment.objects.filter(student=self.request.user.student_profile).order_by('-created_at')

    def create(self, request, *args, **kwargs):
        if request.user.role != 'STUDENT':
            return Response({"detail": "Only students can initiate payments."}, status=status.HTTP_403_FORBIDDEN)
            
        student = request.user.student_profile
        amount = request.data.get('amount')
        method = request.data.get('method')
        transaction_id = request.data.get('transaction_id')

        # Prevent double payments using transaction_id unique check
        if Payment.objects.filter(transaction_id=transaction_id).exists():
            return Response({"detail": "This transaction ID has already been registered."}, status=status.HTTP_400_BAD_REQUEST)

        # Prevent double payments check for same student if successful payment exists
        # Let's say only one fee payment of 1000 is allowed
        # (Allows multiple payments but prevents immediate duplicates in database concurrency)
        if Payment.objects.filter(student=student, transaction_id=transaction_id).exists():
            return Response({"detail": "Duplicate payment detected."}, status=status.HTTP_400_BAD_REQUEST)

        payment = Payment.objects.create(
            student=student,
            amount=amount,
            method=method,
            transaction_id=transaction_id,
            status='SUCCESSFUL', # Mock immediate success
            paid_at=timezone.now()
        )

        Notification.objects.create(
            user=student.user,
            title="Fee Payment Successful",
            message=f"Thank you! Your payment of ₹{payment.amount} (Transaction ID: {payment.transaction_id}) was processed successfully. You can download your receipt now.",
            email_sent=True
        )

        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def receipt(self, request, pk=None):
        payment = self.get_object()
        
        # Verify access control
        if request.user.role != 'ADMIN' and payment.student.user != request.user:
            return Response({"detail": "Unauthorized access to this receipt."}, status=status.HTTP_403_FORBIDDEN)

        pdf_content = generate_receipt_pdf(payment)
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="receipt_{payment.transaction_id}.pdf"'
        return response


# ==========================================
# CHATBOT API
# ==========================================

class ChatbotAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        message = request.data.get('message', '')
        if not message:
            return Response({"response": "Please type a message first!"})
        
        reply = chatbot_response(message)
        return Response({"response": reply})


# ==========================================
# REPORTS & EXPORTS
# ==========================================

class ExportReportsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'ADMIN':
            return Response({"detail": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
            
        report_type = request.query_params.get('type') # students, rooms, payments, occupancy
        export_format = request.query_params.get('format') # excel, pdf
        
        if report_type not in ['students', 'rooms', 'payments', 'occupancy'] or export_format not in ['excel', 'pdf']:
            return Response({"detail": "Invalid parameters."}, status=status.HTTP_400_BAD_REQUEST)
            
        if export_format == 'excel':
            return self.export_excel(report_type)
        else:
            return self.export_pdf(report_type)

    def export_excel(self, report_type):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = report_type.capitalize()
        
        if report_type == 'students':
            headers = ["Student Name", "Student ID", "Email", "Phone", "Gender", "Course", "Department", "Year of Study", "Status"]
            ws.append(headers)
            for student in StudentProfile.objects.all():
                ws.append([
                    student.full_name,
                    student.student_id,
                    student.user.email,
                    student.phone,
                    student.gender,
                    student.course,
                    student.department,
                    student.year_of_study,
                    student.get_application_status_display()
                ])
        elif report_type == 'rooms':
            headers = ["Block", "Room Number", "Floor", "Capacity", "Occupied Beds", "Available Beds", "Room Type"]
            ws.append(headers)
            for room in Room.objects.all():
                ws.append([
                    room.block.name,
                    room.room_number,
                    room.floor_number,
                    room.capacity,
                    room.occupied_beds,
                    room.available_beds,
                    room.get_room_type_display()
                ])
        elif report_type == 'payments':
            headers = ["Student Name", "Student ID", "Amount", "Method", "Transaction ID", "Status", "Date"]
            ws.append(headers)
            for p in Payment.objects.all():
                ws.append([
                    p.student.full_name,
                    p.student.student_id,
                    p.amount,
                    p.method,
                    p.transaction_id,
                    p.status,
                    p.created_at.strftime('%Y-%m-%d %H:%M')
                ])
        elif report_type == 'occupancy':
            headers = ["Block Name", "Total Rooms", "Total Capacity", "Total Occupied", "Occupancy Rate (%)"]
            ws.append(headers)
            for block in HostelBlock.objects.all():
                rooms = block.rooms.all()
                total_rooms = rooms.count()
                capacity = rooms.aggregate(models.Sum('capacity'))['capacity__sum'] or 0
                occupied = rooms.aggregate(models.Sum('occupied_beds'))['occupied_beds__sum'] or 0
                rate = round((occupied / capacity) * 100, 2) if capacity > 0 else 0
                ws.append([block.name, total_rooms, capacity, occupied, rate])
                
        buffer = BytesIO()
        wb.save(buffer)
        excel_data = buffer.getvalue()
        buffer.close()
        
        response = HttpResponse(excel_data, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report.xlsx"'
        return response

    def export_pdf(self, report_type):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        story = []
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=18,
            textColor=colors.HexColor("#1A365D"),
            spaceAfter=15,
            alignment=1
        )
        
        header_cell_style = ParagraphStyle(
            'HeaderCell',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            textColor=colors.white
        )
        
        body_cell_style = ParagraphStyle(
            'BodyCell',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8
        )
        
        story.append(Paragraph(f"CampusStay Hostel - {report_type.capitalize()} Report", title_style))
        story.append(Paragraph(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        story.append(Spacer(1, 15))
        
        table_data = []
        col_widths = []
        
        if report_type == 'students':
            table_data.append([
                Paragraph("Name", header_cell_style),
                Paragraph("Student ID", header_cell_style),
                Paragraph("Course", header_cell_style),
                Paragraph("Dept", header_cell_style),
                Paragraph("Year", header_cell_style),
                Paragraph("Status", header_cell_style)
            ])
            col_widths = [120, 80, 60, 110, 50, 100]
            for s in StudentProfile.objects.all():
                table_data.append([
                    Paragraph(s.full_name, body_cell_style),
                    Paragraph(s.student_id, body_cell_style),
                    Paragraph(s.course, body_cell_style),
                    Paragraph(s.department, body_cell_style),
                    Paragraph(str(s.year_of_study), body_cell_style),
                    Paragraph(s.get_application_status_display(), body_cell_style)
                ])
        elif report_type == 'rooms':
            table_data.append([
                Paragraph("Block", header_cell_style),
                Paragraph("Room No", header_cell_style),
                Paragraph("Floor", header_cell_style),
                Paragraph("Capacity", header_cell_style),
                Paragraph("Occupied", header_cell_style),
                Paragraph("Type", header_cell_style)
            ])
            col_widths = [100, 70, 70, 70, 70, 140]
            for r in Room.objects.all():
                table_data.append([
                    Paragraph(r.block.name, body_cell_style),
                    Paragraph(r.room_number, body_cell_style),
                    Paragraph(str(r.floor_number), body_cell_style),
                    Paragraph(str(r.capacity), body_cell_style),
                    Paragraph(str(r.occupied_beds), body_cell_style),
                    Paragraph(r.get_room_type_display(), body_cell_style)
                ])
        elif report_type == 'payments':
            table_data.append([
                Paragraph("Student", header_cell_style),
                Paragraph("Amount", header_cell_style),
                Paragraph("Method", header_cell_style),
                Paragraph("Txn ID", header_cell_style),
                Paragraph("Date", header_cell_style)
            ])
            col_widths = [130, 70, 90, 130, 100]
            for p in Payment.objects.all():
                table_data.append([
                    Paragraph(p.student.full_name, body_cell_style),
                    Paragraph(f"₹{p.amount}", body_cell_style),
                    Paragraph(p.method, body_cell_style),
                    Paragraph(p.transaction_id, body_cell_style),
                    Paragraph(p.created_at.strftime('%Y-%m-%d'), body_cell_style)
                ])
        elif report_type == 'occupancy':
            table_data.append([
                Paragraph("Block Name", header_cell_style),
                Paragraph("Total Rooms", header_cell_style),
                Paragraph("Capacity", header_cell_style),
                Paragraph("Occupied", header_cell_style),
                Paragraph("Rate (%)", header_cell_style)
            ])
            col_widths = [130, 100, 100, 100, 90]
            for block in HostelBlock.objects.all():
                rooms = block.rooms.all()
                total_rooms = rooms.count()
                capacity = rooms.aggregate(models.Sum('capacity'))['capacity__sum'] or 0
                occupied = rooms.aggregate(models.Sum('occupied_beds'))['occupied_beds__sum'] or 0
                rate = round((occupied / capacity) * 100, 2) if capacity > 0 else 0
                table_data.append([
                    Paragraph(block.name, body_cell_style),
                    Paragraph(str(total_rooms), body_cell_style),
                    Paragraph(str(capacity), body_cell_style),
                    Paragraph(str(occupied), body_cell_style),
                    Paragraph(f"{rate}%", body_cell_style)
                ])

        t = Table(table_data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1A365D")),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F7FAFC")]),
            ('PADDING', (0,0), (-1,-1), 8),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        
        story.append(t)
        doc.build(story)
        pdf_data = buffer.getvalue()
        buffer.close()
        
        response = HttpResponse(pdf_data, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report.pdf"'
        return response


# ==========================================
# ASSISTANT FUNCTIONS
# ==========================================

def recommend_rooms(student):
    rooms = Room.objects.filter(occupied_beds__lt=models.F('capacity'))
    
    recommendations = []
    for room in rooms:
        # Check current occupants
        allocations = RoomAllocation.objects.filter(room=room, status='ACTIVE')
        occupants = [a.student for a in allocations]
        
        # Gender rule
        if occupants and occupants[0].gender != student.gender:
            continue
            
        score = 40 # Base score
        
        # Course compatibility
        course_match = sum(1 for o in occupants if getattr(o, 'course', '') == student.course)
        score += course_match * 15

        # Department compatibility
        dept_match = sum(1 for o in occupants if o.department == student.department)
        score += dept_match * 15
        
        # Academic year compatibility
        year_match = sum(1 for o in occupants if o.year_of_study == student.year_of_study)
        score += year_match * 15
        
        # Room Type Preferences
        if room.room_type == 'SINGLE':
            score += 15
        elif room.room_type == 'DOUBLE':
            score += 10
        else:
            score += 5
            
        score = min(100, score)
        
        recommendations.append({
            'room_id': room.id,
            'room_number': room.room_number,
            'block_name': room.block.name,
            'floor_number': room.floor_number,
            'capacity': room.capacity,
            'occupied_beds': room.occupied_beds,
            'available_beds': room.available_beds,
            'room_type': room.get_room_type_display(),
            'score': score,
            'reason': f"Matches gender ({student.gender}). " + 
                     (f"Has roommate(s) in same course ({course_match}). " if course_match else "") +
                     (f"Has roommate(s) in same department ({dept_match}). " if dept_match else "") +
                     (f"Has roommate(s) in same year ({year_match}). " if year_match else "Available space.")
        })
        
    recommendations.sort(key=lambda x: x['score'], reverse=True)
    return recommendations[:3]

def chatbot_response(query):
    query = query.lower().strip()
    
    intents = [
        {
            'keywords': ['fee', 'payment', 'pay', 'cost', 'charge', 'receipt'],
            'response': "Hostel fees can be paid directly through the 'Payments' section on your dashboard. We support UPI, Debit/Credit Cards, and Net Banking. Once successful, you can download the receipt PDF immediately."
        },
        {
            'keywords': ['change', 'swap', 'move', 'transfer'],
            'response': "If you want to request a room change, go to 'Room Details' on your student dashboard and fill out the 'Room Change Request' form. Your application will be reviewed by the hostel administrator."
        },
        {
            'keywords': ['complaint', 'issue', 'repair', 'plumbing', 'electrical', 'wifi', 'internet', 'broken'],
            'response': "For maintenance issues or complaints (e.g. plumbing, electrical, wifi, housekeeping), please submit a ticket in the 'Complaints' tab. Our warden team reviews and resolves complaints, updating their status in real-time."
        },
        {
            'keywords': ['wifi', 'internet', 'password'],
            'response': "Free high-speed campus WiFi is available in all hostel blocks. The SSID is 'CampusStay-WiFi'. You can log in using your Student ID and the system-generated network password."
        },
        {
            'keywords': ['food', 'mess', 'canteen', 'dining', 'meal'],
            'response': "The hostel mess serves breakfast (7:30 AM - 9:00 AM), lunch (12:30 PM - 2:00 PM), and dinner (7:30 PM - 9:00 PM). Weekly menus are posted on the physical notice board and sent to student portals."
        },
        {
            'keywords': ['time', 'gate', 'curfew', 'entry', 'leave'],
            'response': "The main hostel gates close at 10:00 PM daily. Late entry requires prior approval from the warden, which must be requested in writing at least 4 hours in advance."
        },
        {
            'keywords': ['rule', 'regulation', 'discipline'],
            'response': "Standard rules require maintaining silence during study hours (9:00 PM - 6:00 AM), prohibiting cooking inside rooms, and strictly banning unauthorized visitors inside rooms after 8:00 PM."
        },
        {
            'keywords': ['hello', 'hi', 'hey', 'start'],
            'response': "Hello! I am your CampusStay Hostel Assistant. How can I help you today? You can ask me about hostel fees, room changes, wifi, mess timings, rules, or complaints."
        }
    ]
    
    for intent in intents:
        if any(keyword in query for keyword in intent['keywords']):
            return intent['response']
            
    return "I'm sorry, I couldn't find a direct answer to that. You can contact the main warden's office at warden@campusstay.edu or call +1 555-0199 for assistance."
