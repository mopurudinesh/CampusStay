from rest_framework import serializers
from hostel.models import (
    CustomUser, StudentProfile, HostelBlock, Room, RoomAllocation,
    RoomChangeRequest, Complaint, Feedback, Announcement, Payment, Notification
)
import re

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'email', 'role', 'first_name', 'last_name', 'is_active')

class StudentProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = StudentProfile
        fields = '__all__'

class RegisterSerializer(serializers.Serializer):
    # User fields
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    
    # Profile fields
    full_name = serializers.CharField(max_length=100)
    student_id = serializers.CharField(max_length=20)
    phone = serializers.CharField(max_length=15)
    gender = serializers.CharField(max_length=15)
    course = serializers.CharField(max_length=50)
    department = serializers.CharField(max_length=100)
    year_of_study = serializers.IntegerField()
    batch = serializers.CharField(max_length=20, required=False, default='2022 to 2026')
    address = serializers.CharField()
    parent_contact = serializers.CharField(max_length=15)
    profile_photo = serializers.ImageField(required=False, allow_null=True)

    def validate_username(self, value):
        if CustomUser.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists.")
        return value

    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_student_id(self, value):
        if StudentProfile.objects.filter(student_id=value).exists():
            raise serializers.ValidationError("A student with this Student ID is already registered.")
        return value

    def validate_phone(self, value):
        if not re.match(r'^\+?[0-9]{10,15}$', value):
            raise serializers.ValidationError("Phone number must be between 10 and 15 digits, and optionally start with '+'.")
        return value

    def validate_parent_contact(self, value):
        if not re.match(r'^\+?[0-9]{10,15}$', value):
            raise serializers.ValidationError("Parent/Guardian contact number must be between 10 and 15 digits, and optionally start with '+'.")
        return value

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        
        password = data['password']
        if len(password) < 8:
            raise serializers.ValidationError({"password": "Password must be at least 8 characters long."})
        if not any(char.isupper() for char in password):
            raise serializers.ValidationError({"password": "Password must contain at least one uppercase letter."})
        if not any(char.islower() for char in password):
            raise serializers.ValidationError({"password": "Password must contain at least one lowercase letter."})
        if not any(char.isdigit() for char in password):
            raise serializers.ValidationError({"password": "Password must contain at least one digit."})
        if not any(char in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for char in password):
            raise serializers.ValidationError({"password": "Password must contain at least one special character."})
            
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        username = validated_data.pop('username')
        email = validated_data.pop('email')
        password = validated_data.pop('password')
        
        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            role='STUDENT'
        )
        
        profile = StudentProfile.objects.create(
            user=user,
            **validated_data
        )
        
        Notification.objects.create(
            user=user,
            title="Registration Submitted Successfully",
            message=f"Welcome to CampusStay, {profile.full_name}! Your hostel registration application (ID: {profile.student_id}) has been submitted and is currently pending review.",
            email_sent=True
        )
        
        return profile

class HostelBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostelBlock
        fields = '__all__'

class RoomSerializer(serializers.ModelSerializer):
    block_name = serializers.CharField(source='block.name', read_only=True)
    available_beds = serializers.IntegerField(read_only=True)
    capacity = serializers.IntegerField(required=False, allow_null=True)
    yearly_fee = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    
    class Meta:
        model = Room
        fields = '__all__'

class RoomAllocationSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    student_id = serializers.CharField(source='student.student_id', read_only=True)
    room_number = serializers.CharField(source='room.room_number', read_only=True)
    block_name = serializers.CharField(source='room.block.name', read_only=True)
    
    class Meta:
        model = RoomAllocation
        fields = '__all__'

class RoomChangeRequestSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    current_room_details = serializers.CharField(source='current_room.__str__', read_only=True)
    preferred_block_name = serializers.CharField(source='preferred_block.name', read_only=True)
    
    class Meta:
        model = RoomChangeRequest
        fields = '__all__'
        read_only_fields = ('student', 'current_room')

class ComplaintSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    
    class Meta:
        model = Complaint
        fields = '__all__'
        read_only_fields = ('student',)

class FeedbackSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    
    class Meta:
        model = Feedback
        fields = '__all__'
        read_only_fields = ('student',)

class AnnouncementSerializer(serializers.ModelSerializer):
    posted_by_name = serializers.CharField(source='posted_by.username', read_only=True)
    
    class Meta:
        model = Announcement
        fields = '__all__'

class PaymentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ('student',)

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'
