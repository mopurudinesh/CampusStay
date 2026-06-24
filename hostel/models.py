import os
from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('STUDENT', 'Student'),
        ('ADMIN', 'Admin'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='STUDENT')
    email = models.EmailField(unique=True)

    def __str__(self):
        return f"{self.username} ({self.role})"

class StudentProfile(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('UNDER_REVIEW', 'Under Review'),
        ('APPROVED', 'Approved'),
        ('ROOM_ALLOCATED', 'Room Allocated'),
        ('REJECTED', 'Rejected'),
        ('ON_HOLD', 'On Hold'),
    )
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='student_profile')
    full_name = models.CharField(max_length=100)
    student_id = models.CharField(max_length=20, unique=True)
    phone = models.CharField(max_length=15)
    gender = models.CharField(max_length=15)
    course = models.CharField(max_length=50, default='B.E.')
    department = models.CharField(max_length=100)
    year_of_study = models.IntegerField()
    batch = models.CharField(max_length=20, default='2022 to 2026')
    address = models.TextField()
    parent_contact = models.CharField(max_length=15)
    profile_photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True)
    application_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    additional_info_requested = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.full_name} ({self.student_id})"

class HostelBlock(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

class Room(models.Model):
    ROOM_TYPE_CHOICES = (
        ('SINGLE', 'Single Sharing'),
        ('DOUBLE', 'Double Sharing'),
        ('TRIPLE', 'Triple Sharing'),
        ('FOUR', 'Four Sharing'),
    )
    block = models.ForeignKey(HostelBlock, on_delete=models.CASCADE, related_name='rooms')
    room_number = models.CharField(max_length=10)
    floor_number = models.IntegerField()
    capacity = models.IntegerField(null=True, blank=True)
    occupied_beds = models.IntegerField(default=0)
    room_type = models.CharField(max_length=10, choices=ROOM_TYPE_CHOICES, default='SINGLE')
    is_ac = models.BooleanField(default=False)
    yearly_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    room_photo = models.ImageField(upload_to='room_photos/', null=True, blank=True)

    class Meta:
        unique_together = ('block', 'room_number')

    @property
    def available_beds(self):
        return max(0, self.capacity - self.occupied_beds)

    def save(self, *args, **kwargs):
        if self.capacity is None:
            if self.room_type == 'SINGLE':
                self.capacity = 1
            elif self.room_type == 'DOUBLE':
                self.capacity = 2
            elif self.room_type == 'TRIPLE':
                self.capacity = 3
            elif self.room_type == 'FOUR':
                self.capacity = 4
            else:
                self.capacity = 1
        if self.yearly_fee is None:
            base_fees = {
                'SINGLE': 100000.00,
                'DOUBLE': 90000.00,
                'TRIPLE': 80000.00,
                'FOUR': 70000.00,
            }
            base_fee = base_fees.get(self.room_type, 90000.00)
            if self.is_ac:
                base_fee += 50000.00
            self.yearly_fee = base_fee
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.block.name} - Room {self.room_number}"

class RoomAllocation(models.Model):
    STATUS_CHOICES = (
        ('ACTIVE', 'Active'),
        ('VACATED', 'Vacated'),
        ('CHANGED', 'Changed'),
    )
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='allocations')
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='allocations')
    allocated_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ACTIVE')
    vacated_at = models.DateTimeField(null=True, blank=True)
    bed_number = models.CharField(max_length=15, null=True, blank=True)

    def __str__(self):
        return f"{self.student.full_name} -> {self.room}"

class RoomChangeRequest(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    )
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='room_change_requests')
    current_room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='change_from_requests')
    preferred_block = models.ForeignKey(HostelBlock, on_delete=models.SET_NULL, null=True, blank=True)
    preferred_room_type = models.CharField(max_length=10, choices=Room.ROOM_TYPE_CHOICES, null=True, blank=True)
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    admin_remarks = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Change Request: {self.student.full_name}"

class Complaint(models.Model):
    CATEGORY_CHOICES = (
        ('PLUMBING', 'Plumbing'),
        ('ELECTRICAL', 'Electrical'),
        ('INTERNET', 'Internet/WiFi'),
        ('ROOMMATE', 'Roommate Issue'),
        ('CLEANING', 'Cleaning/Housekeeping'),
        ('OTHERS', 'Others'),
    )
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('RESOLVED', 'Resolved'),
    )
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='complaints')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description = models.TextField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')
    admin_remarks = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Complaint {self.id}: {self.category} ({self.status})"

class Feedback(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='feedback')
    overall_rating = models.IntegerField()
    cleanliness_rating = models.IntegerField()
    food_rating = models.IntegerField()
    warden_rating = models.IntegerField()
    comments = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback from {self.student.full_name}"

class Announcement(models.Model):
    TARGET_CHOICES = (
        ('ALL', 'All Users'),
        ('STUDENT', 'Students Only'),
        ('ADMIN', 'Admins Only'),
    )
    title = models.CharField(max_length=150)
    content = models.TextField()
    posted_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='announcements')
    target_role = models.CharField(max_length=10, choices=TARGET_CHOICES, default='ALL')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Payment(models.Model):
    METHOD_CHOICES = (
        ('UPI', 'UPI'),
        ('DEBIT_CARD', 'Debit Card'),
        ('CREDIT_CARD', 'Credit Card'),
        ('NET_BANKING', 'Net Banking'),
    )
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('SUCCESSFUL', 'Successful'),
        ('FAILED', 'Failed'),
    )
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    transaction_id = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.transaction_id} ({self.status})"

class Notification(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=150)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user.username}: {self.title}"
