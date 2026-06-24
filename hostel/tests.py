from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from hostel.models import HostelBlock, Room, StudentProfile, RoomAllocation, Payment, Complaint, RoomChangeRequest, Announcement, Notification
import json

User = get_user_model()

class HostelSystemTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        
        # Create standard admin user
        self.admin_user = User.objects.create_user(
            username="adminuser",
            email="admin@campusstay.edu",
            password="SecureAdmin123!",
            role="ADMIN"
        )
        
        # Create or fetch a mock block
        self.block_a, _ = HostelBlock.objects.get_or_create(name="Block A", defaults={"description": "Main Boys Block"})
        
        # Create mock rooms
        self.room_101 = Room.objects.create(
            block=self.block_a,
            room_number="101",
            floor_number=1,
            capacity=2,
            occupied_beds=0,
            room_type="DOUBLE"
        )
        
        self.room_102 = Room.objects.create(
            block=self.block_a,
            room_number="102",
            floor_number=1,
            capacity=1,
            occupied_beds=0,
            room_type="SINGLE"
        )

        # Standard student registration data
        self.registration_data = {
            "username": "studentjohndoe",
            "email": "john@university.edu",
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!",
            "full_name": "John Doe",
            "student_id": "STU8877",
            "phone": "9876543210",
            "gender": "Male",
            "course": "B.E.",
            "department": "Computer Science",
            "year_of_study": 2,
            "address": "123 Main St, Tech City",
            "parent_contact": "9876543211"
        }

    # ====================================================
    # 1. REGISTRATION VALIDATIONS (6 cases)
    # ====================================================

    def test_registration_success(self):
        url = reverse('api_register')
        response = self.client.post(url, self.registration_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(StudentProfile.objects.filter(student_id="STU8877").exists())

    def test_registration_required_fields(self):
        incomplete_data = self.registration_data.copy()
        incomplete_data.pop("student_id")
        url = reverse('api_register')
        response = self.client.post(url, incomplete_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_invalid_email(self):
        bad_email_data = self.registration_data.copy()
        bad_email_data["email"] = "not_an_email"
        url = reverse('api_register')
        response = self.client.post(url, bad_email_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_invalid_phone(self):
        bad_phone_data = self.registration_data.copy()
        bad_phone_data["phone"] = "123" # too short
        url = reverse('api_register')
        response = self.client.post(url, bad_phone_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_duplicate_email(self):
        # Create pre-existing user with email
        User.objects.create_user(username="preexisting", email="john@university.edu", password="SomePassword123!")
        url = reverse('api_register')
        response = self.client.post(url, self.registration_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_registration_duplicate_student_id(self):
        # Create student with student_id
        url = reverse('api_register')
        self.client.post(url, self.registration_data, format='json')
        
        # Try registering second student with same Student ID
        second_student = self.registration_data.copy()
        second_student["username"] = "anotherusername"
        second_student["email"] = "another@university.edu"
        
        response = self.client.post(url, second_student, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("student_id", response.data)

    # ====================================================
    # 2. PASSWORD STRENGTH VALIDATIONS (6 cases)
    # ====================================================

    def test_password_too_short(self):
        bad_pass = self.registration_data.copy()
        bad_pass["password"] = "Short1!"
        bad_pass["confirm_password"] = "Short1!"
        response = self.client.post(reverse('api_register'), bad_pass, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_no_upper(self):
        bad_pass = self.registration_data.copy()
        bad_pass["password"] = "noupper123!"
        bad_pass["confirm_password"] = "noupper123!"
        response = self.client.post(reverse('api_register'), bad_pass, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_no_lower(self):
        bad_pass = self.registration_data.copy()
        bad_pass["password"] = "NOLOWER123!"
        bad_pass["confirm_password"] = "NOLOWER123!"
        response = self.client.post(reverse('api_register'), bad_pass, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_no_digit(self):
        bad_pass = self.registration_data.copy()
        bad_pass["password"] = "NoDigitsHere!"
        bad_pass["confirm_password"] = "NoDigitsHere!"
        response = self.client.post(reverse('api_register'), bad_pass, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_no_special(self):
        bad_pass = self.registration_data.copy()
        bad_pass["password"] = "NoSpecial12345"
        bad_pass["confirm_password"] = "NoSpecial12345"
        response = self.client.post(reverse('api_register'), bad_pass, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_passwords_mismatch(self):
        bad_pass = self.registration_data.copy()
        bad_pass["password"] = "Passphrase123!"
        bad_pass["confirm_password"] = "Different123!"
        response = self.client.post(reverse('api_register'), bad_pass, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ====================================================
    # 3. AUTHENTICATION & JWT TOKEN ACCESS (3 cases)
    # ====================================================

    def test_login_success(self):
        # Register first
        self.client.post(reverse('api_register'), self.registration_data, format='json')
        
        # Test login
        response = self.client.post(reverse('api_login'), {
            "username": "studentjohndoe",
            "password": "SecurePassword123!"
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_login_via_student_id_success(self):
        # Register first
        self.client.post(reverse('api_register'), self.registration_data, format='json')
        
        # Test login using student_id
        response = self.client.post(reverse('api_login'), {
            "username": "STU8877",
            "password": "SecurePassword123!"
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_login_invalid_credentials(self):
        response = self.client.post(reverse('api_login'), {
            "username": "nonexistent",
            "password": "WrongPassword!"
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_details_requires_authentication(self):
        response = self.client.get(reverse('api_user_details'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ====================================================
    # 4. STATUS TIMELINE FLOW & WARDEN REVIEW (5 cases)
    # ====================================================

    def test_verify_email_status_transition(self):
        # Register
        self.client.post(reverse('api_register'), self.registration_data, format='json')
        profile = StudentProfile.objects.get(student_id="STU8877")
        self.assertEqual(profile.application_status, "PENDING")
        
        # Verify
        response = self.client.post(reverse('api_verify_email'), {
            "student_id": "STU8877",
            "code": "123456"
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        profile.refresh_from_db()
        self.assertEqual(profile.application_status, "UNDER_REVIEW")

    def test_admin_approve_application(self):
        self.client.post(reverse('api_register'), self.registration_data, format='json')
        profile = StudentProfile.objects.get(student_id="STU8877")
        
        # Admin Login
        self.client.force_authenticate(user=self.admin_user)
        
        # Approve
        url = reverse('application-update-status', kwargs={'pk': profile.id})
        response = self.client.post(url, {"status": "APPROVED"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        profile.refresh_from_db()
        self.assertEqual(profile.application_status, "APPROVED")

    def test_admin_reject_application(self):
        self.client.post(reverse('api_register'), self.registration_data, format='json')
        profile = StudentProfile.objects.get(student_id="STU8877")
        
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('application-update-status', kwargs={'pk': profile.id})
        response = self.client.post(url, {"status": "REJECTED"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        profile.refresh_from_db()
        self.assertEqual(profile.application_status, "REJECTED")

    def test_admin_hold_application_with_remarks(self):
        self.client.post(reverse('api_register'), self.registration_data, format='json')
        profile = StudentProfile.objects.get(student_id="STU8877")
        
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('application-update-status', kwargs={'pk': profile.id})
        response = self.client.post(url, {"status": "ON_HOLD", "remarks": "Missing parent signature."}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        profile.refresh_from_db()
        self.assertEqual(profile.application_status, "ON_HOLD")
        self.assertEqual(profile.additional_info_requested, "Missing parent signature.")

    def test_unauthorized_status_update(self):
        self.client.post(reverse('api_register'), self.registration_data, format='json')
        profile = StudentProfile.objects.get(student_id="STU8877")
        
        # Authenticate as student
        self.client.force_authenticate(user=profile.user)
        
        url = reverse('application-update-status', kwargs={'pk': profile.id})
        response = self.client.post(url, {"status": "APPROVED"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ====================================================
    # 5. ROOM ALLOCATION & CAPACITY LIMITS (6 cases)
    # ====================================================

    def test_create_room_duplicate_constraints(self):
        # Trying to create Room 101 in Block A again (unique_together constraint)
        with self.assertRaises(Exception):
            Room.objects.create(
                block=self.block_a,
                room_number="101",
                floor_number=1,
                capacity=3
            )

    def test_room_capacity_available(self):
        self.assertEqual(self.room_101.available_beds, 2)

    def test_allocate_room_success(self):
        self.client.post(reverse('api_register'), self.registration_data, format='json')
        profile = StudentProfile.objects.get(student_id="STU8877")
        
        # Approve student first
        profile.application_status = "APPROVED"
        profile.save()
        
        # Allocate Room
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('room-allocate', kwargs={'pk': self.room_101.id})
        response = self.client.post(url, {"student_id": "STU8877"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.room_101.refresh_from_db()
        self.assertEqual(self.room_101.occupied_beds, 1)
        
        profile.refresh_from_db()
        self.assertEqual(profile.application_status, "ROOM_ALLOCATED")
        self.assertTrue(RoomAllocation.objects.filter(student=profile, room=self.room_101, status='ACTIVE').exists())

    def test_allocate_room_with_bed_number_success(self):
        self.client.post(reverse('api_register'), self.registration_data, format='json')
        profile = StudentProfile.objects.get(student_id="STU8877")
        
        profile.application_status = "APPROVED"
        profile.save()
        
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('room-allocate', kwargs={'pk': self.room_101.id})
        response = self.client.post(url, {"student_id": "STU8877", "bed_number": "Bed B"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that allocation has the correct bed_number
        alloc = RoomAllocation.objects.get(student=profile, room=self.room_101, status='ACTIVE')
        self.assertEqual(alloc.bed_number, "Bed B")
        
        # Check student dashboard returns the bed_number
        self.client.force_authenticate(user=profile.user)
        dash_url = reverse('api_student_dashboard')
        dash_res = self.client.get(dash_url)
        self.assertEqual(dash_res.status_code, status.HTTP_200_OK)
        self.assertEqual(dash_res.data["room"]["bed_number"], "Bed B")

    def test_room_capacity_auto_calculation(self):
        room_single = Room.objects.create(
            block=self.block_a,
            room_number="999",
            floor_number=1,
            room_type="SINGLE"
        )
        self.assertEqual(room_single.capacity, 1)

        room_double = Room.objects.create(
            block=self.block_a,
            room_number="998",
            floor_number=1,
            room_type="DOUBLE"
        )
        self.assertEqual(room_double.capacity, 2)

        room_triple = Room.objects.create(
            block=self.block_a,
            room_number="997",
            floor_number=1,
            room_type="TRIPLE"
        )
        self.assertEqual(room_triple.capacity, 3)

        room_four = Room.objects.create(
            block=self.block_a,
            room_number="996",
            floor_number=1,
            room_type="FOUR"
        )
        self.assertEqual(room_four.capacity, 4)

    def test_room_default_yearly_fees(self):
        room_single_nac = Room.objects.create(
            block=self.block_a, room_number="901", floor_number=1, room_type="SINGLE", is_ac=False
        )
        self.assertEqual(room_single_nac.yearly_fee, 100000.00)

        room_single_ac = Room.objects.create(
            block=self.block_a, room_number="902", floor_number=1, room_type="SINGLE", is_ac=True
        )
        self.assertEqual(room_single_ac.yearly_fee, 150000.00)

        room_double_nac = Room.objects.create(
            block=self.block_a, room_number="903", floor_number=1, room_type="DOUBLE", is_ac=False
        )
        self.assertEqual(room_double_nac.yearly_fee, 90000.00)

        room_four_ac = Room.objects.create(
            block=self.block_a, room_number="904", floor_number=1, room_type="FOUR", is_ac=True
        )
        self.assertEqual(room_four_ac.yearly_fee, 120000.00)

    def test_room_custom_yearly_fee(self):
        room_custom = Room.objects.create(
            block=self.block_a, room_number="905", floor_number=1, room_type="DOUBLE", is_ac=True, yearly_fee=14500.50
        )
        self.assertEqual(room_custom.yearly_fee, 14500.50)

    def test_allocate_room_no_capacity(self):
        self.client.post(reverse('api_register'), self.registration_data, format='json')
        profile = StudentProfile.objects.get(student_id="STU8877")
        profile.application_status = "APPROVED"
        profile.save()
        
        # Setup room 102 as fully occupied
        self.room_102.occupied_beds = 1
        self.room_102.save()
        
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('room-allocate', kwargs={'pk': self.room_102.id})
        response = self.client.post(url, {"student_id": "STU8877"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "No beds available in this room.")

    def test_change_allocation_success(self):
        self.client.post(reverse('api_register'), self.registration_data, format='json')
        profile = StudentProfile.objects.get(student_id="STU8877")
        profile.application_status = "APPROVED"
        profile.save()
        
        # Initial allocation
        RoomAllocation.objects.create(student=profile, room=self.room_101, status='ACTIVE')
        self.room_101.occupied_beds = 1
        self.room_101.save()
        
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('room-change-allocation')
        response = self.client.post(url, {
            "student_id": "STU8877",
            "room_id": self.room_102.id
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.room_101.refresh_from_db()
        self.room_102.refresh_from_db()
        self.assertEqual(self.room_101.occupied_beds, 0)
        self.assertEqual(self.room_102.occupied_beds, 1)

    def test_unauthorized_room_allocation(self):
        self.client.post(reverse('api_register'), self.registration_data, format='json')
        profile = StudentProfile.objects.get(student_id="STU8877")
        
        self.client.force_authenticate(user=profile.user)
        url = reverse('room-allocate', kwargs={'pk': self.room_101.id})
        response = self.client.post(url, {"student_id": "STU8877"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ====================================================
    # 6. PAYMENTS & CONCURRENCY SECURITY (4 cases)
    # ====================================================

    def test_make_payment_success(self):
        self.client.post(reverse('api_register'), self.registration_data, format='json')
        profile = StudentProfile.objects.get(student_id="STU8877")
        
        self.client.force_authenticate(user=profile.user)
        url = reverse('payment-list')
        response = self.client.post(url, {
            "amount": "1200.00",
            "method": "UPI",
            "transaction_id": "TXN_MOCK_XYZ"
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "SUCCESSFUL")

    def test_duplicate_payment_prevention(self):
        self.client.post(reverse('api_register'), self.registration_data, format='json')
        profile = StudentProfile.objects.get(student_id="STU8877")
        
        self.client.force_authenticate(user=profile.user)
        url = reverse('payment-list')
        
        # Payment 1
        self.client.post(url, {
            "amount": "1200.00",
            "method": "UPI",
            "transaction_id": "TXN_MOCK_XYZ"
        }, format='json')
        
        # Re-submit duplicate transaction ID
        response = self.client.post(url, {
            "amount": "1200.00",
            "method": "CREDIT_CARD",
            "transaction_id": "TXN_MOCK_XYZ"
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthorized_receipt_download(self):
        # Register Student 1
        self.client.post(reverse('api_register'), self.registration_data, format='json')
        student1 = StudentProfile.objects.get(student_id="STU8877")
        p1 = Payment.objects.create(student=student1, amount=1200, method="UPI", transaction_id="TXN1", status="SUCCESSFUL")
        
        # Register Student 2
        student2_data = self.registration_data.copy()
        student2_data["username"] = "student2"
        student2_data["email"] = "stu2@univ.edu"
        student2_data["student_id"] = "STU9900"
        self.client.post(reverse('api_register'), student2_data, format='json')
        student2 = StudentProfile.objects.get(student_id="STU9900")
        
        # Authenticate as Student 2 and try to download Student 1's receipt
        self.client.force_authenticate(user=student2.user)
        url = reverse('payment-receipt', kwargs={'pk': p1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_download_receipt_success(self):
        self.client.post(reverse('api_register'), self.registration_data, format='json')
        profile = StudentProfile.objects.get(student_id="STU8877")
        p = Payment.objects.create(student=profile, amount=1200, method="UPI", transaction_id="TXN1", status="SUCCESSFUL")
        
        self.client.force_authenticate(user=profile.user)
        url = reverse('payment-receipt', kwargs={'pk': p.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['content-type'], 'application/pdf')

    # ====================================================
    # 7. ADVANCED SERVICES (4 cases)
    # ====================================================

    def test_chatbot_intent_matching(self):
        self.client.post(reverse('api_register'), self.registration_data, format='json')
        profile = StudentProfile.objects.get(student_id="STU8877")
        
        self.client.force_authenticate(user=profile.user)
        response = self.client.post(reverse('api_chatbot'), {"message": "How do I pay fees?"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("payments", response.data["response"].lower())

    def test_room_recommendation_gender_matching(self):
        # Allocate Room 101 to a Female student
        female_student = User.objects.create_user(username="female", email="fe@univ.edu", password="Password123!", role="STUDENT")
        f_profile = StudentProfile.objects.create(user=female_student, full_name="Jane Doe", student_id="STU3344", gender="Female", course="B.E.", year_of_study=2)
        RoomAllocation.objects.create(student=f_profile, room=self.room_101, status='ACTIVE')
        self.room_101.occupied_beds = 1
        self.room_101.save()
        
        # Authenticate as Male student John Doe
        self.client.post(reverse('api_register'), self.registration_data, format='json')
        male_profile = StudentProfile.objects.get(student_id="STU8877")
        self.client.force_authenticate(user=male_profile.user)
        
        # Recommendations shouldn't include Room 101 because female Jane occupies it
        response = self.client.get(reverse('room-recommendations'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        room_ids = [r['room_id'] for r in response.data]
        self.assertNotIn(self.room_101.id, room_ids)

    def test_room_recommendation_score_compatibility(self):
        # Allocate Room 101 to a Male student from CSE department
        cse_student = User.objects.create_user(username="cseboy", email="cse@univ.edu", password="Password123!", role="STUDENT")
        cse_profile = StudentProfile.objects.create(user=cse_student, full_name="CSE Boy", student_id="STU9988", gender="Male", course="B.E.", department="Computer Science", year_of_study=2)
        RoomAllocation.objects.create(student=cse_profile, room=self.room_101, status='ACTIVE')
        self.room_101.occupied_beds = 1
        self.room_101.save()
        
        # Authenticate as CSE Year 2 Male student John Doe
        self.client.post(reverse('api_register'), self.registration_data, format='json')
        profile = StudentProfile.objects.get(student_id="STU8877")
        self.client.force_authenticate(user=profile.user)
        
        response = self.client.get(reverse('room-recommendations'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Room 101 should score higher than empty Single Room 102 due to department/year compatibility rules
        rec_101 = next(r for r in response.data if r['room_id'] == self.room_101.id)
        rec_102 = next(r for r in response.data if r['room_id'] == self.room_102.id)
        
        # Room 101 matches department (+15) and year (+15) -> scores higher than base single
        self.assertGreater(rec_101['score'], rec_102['score'])

    def test_raise_complaint_and_resolve(self):
        self.client.post(reverse('api_register'), self.registration_data, format='json')
        profile = StudentProfile.objects.get(student_id="STU8877")
        
        # Student creates complaint
        self.client.force_authenticate(user=profile.user)
        url = reverse('complaint-list')
        self.client.post(url, {"category": "PLUMBING", "description": "Sink tap leaking."}, format='json')
        
        complaint = Complaint.objects.get(student=profile)
        self.assertEqual(complaint.status, "PENDING")
        
        # Admin resolves complaint
        self.client.force_authenticate(user=self.admin_user)
        res_url = reverse('complaint-update-status', kwargs={'pk': complaint.id})
        response = self.client.post(res_url, {"status": "RESOLVED", "remarks": "Plumber replaced the washer."}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, "RESOLVED")
        self.assertEqual(complaint.admin_remarks, "Plumber replaced the washer.")

    # ====================================================
    # 8. ADMINISTRATIVE BLOCK AND DELETE USERS (2 cases)
    # ====================================================

    def test_block_student_success(self):
        self.client.post(reverse('api_register'), self.registration_data, format='json')
        profile = StudentProfile.objects.get(student_id="STU8877")
        user = profile.user
        self.assertTrue(user.is_active)

        # Authenticate as Admin
        self.client.force_authenticate(user=self.admin_user)
        
        # Block the user
        url = reverse('application-toggle-active', kwargs={'pk': profile.id})
        response = self.client.post(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        user.refresh_from_db()
        self.assertFalse(user.is_active)
        
        # Verify blocked student cannot log in
        self.client.logout()
        login_res = self.client.post(reverse('api_login'), {
            "username": "studentjohndoe",
            "password": "SecurePassword123!"
        }, format='json')
        self.assertEqual(login_res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_student_cascading_success(self):
        self.client.post(reverse('api_register'), self.registration_data, format='json')
        profile = StudentProfile.objects.get(student_id="STU8877")
        user = profile.user
        
        # Approve and allocate student to Room 101
        profile.application_status = "APPROVED"
        profile.save()
        
        # Allocate
        self.client.force_authenticate(user=self.admin_user)
        alloc_url = reverse('room-allocate', kwargs={'pk': self.room_101.id})
        self.client.post(alloc_url, {"student_id": "STU8877"}, format='json')
        
        self.room_101.refresh_from_db()
        self.assertEqual(self.room_101.occupied_beds, 1)
        
        # Delete student via Admin
        delete_url = reverse('application-detail', kwargs={'pk': profile.id})
        response = self.client.delete(delete_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify User and Profile are deleted
        self.assertFalse(User.objects.filter(username="studentjohndoe").exists())
        self.assertFalse(StudentProfile.objects.filter(student_id="STU8877").exists())
        
        # Verify Room 101 occupied_beds is decremented back to 0
        self.room_101.refresh_from_db()
        self.assertEqual(self.room_101.occupied_beds, 0)
