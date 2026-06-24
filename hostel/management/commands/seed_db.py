from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from hostel.models import StudentProfile, HostelBlock, Room

class Command(BaseCommand):
    help = 'Seeds the database with default users, blocks, and rooms'

    def handle(self, *args, **options):
        User = get_user_model()

        # 1. Create Admin
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@campusstay.com',
                'role': 'ADMIN',
                'is_active': True
            }
        )
        if created:
            admin_user.set_password('Admin@12345')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('Admin user created successfully.'))
        else:
            self.stdout.write('Admin user already exists.')

        # 2. Create Blocks
        blocks = {}
        for block_name in ['Block A', 'Block B', 'Block C']:
            block, created = HostelBlock.objects.get_or_create(name=block_name)
            blocks[block_name] = block
            if created:
                self.stdout.write(self.style.SUCCESS(f'Block {block_name} created.'))

        # 3. Create Rooms
        rooms_to_create = [
            {'room_number': '301', 'block': 'Block A', 'room_type': 'FOUR', 'capacity': 4},
            {'room_number': '201', 'block': 'Block A', 'room_type': 'TRIPLE', 'capacity': 3},
        ]
        for room_data in rooms_to_create:
            block = blocks[room_data['block']]
            room, created = Room.objects.get_or_create(
                block=block,
                room_number=room_data['room_number'],
                defaults={
                    'room_type': room_data['room_type'],
                    'capacity': room_data['capacity']
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Room {room_data['room_number']} in {room_data['block']} created."))

        # 4. Create Students
        students_data = [
            {
                'username': 'Dinesh',
                'email': 'dineshkumarmopuru@gmail.com',
                'password': 'Dinesh@2004',
                'full_name': 'Mopuru Dinesh',
                'student_id': '192211706',
                'phone': '8098876223',
                'gender': 'Male',
                'course': 'B.E.',
                'department': 'Computer Science and Engineering',
                'year_of_study': 1,
                'batch': '2022 to 2026',
                'address': '11-16 EGUVAPATTU SALI STREET NARAYANAVANAM, PUTTUR, TIRUPATHI DISTRICT, ANDHRA PRRADESH',
                'parent_contact': '8098876223'
            },
            {
                'username': 'Charan Sai',
                'email': 'bandicharansaireddy@gmail.com',
                'password': 'Charan@12345',
                'full_name': 'Bandi Charan Sai Reddy',
                'student_id': '192210022',
                'phone': '6281397848',
                'gender': 'Male',
                'course': 'B.E.',
                'department': 'Computer Science and Engineering',
                'year_of_study': 2,
                'batch': '2022 to 2026',
                'address': 'KG Center Point , Chennai, Tamilnadu',
                'parent_contact': '6281397848'
            },
            {
                'username': 'Krishna',
                'email': 'krishnakarthikeya@gmail.com',
                'password': 'Krishna@12345',
                'full_name': 'Yaramsetty Krishna Karthikeya',
                'student_id': '192210017',
                'phone': '9876543210',
                'gender': 'Male',
                'course': 'B.E.',
                'department': 'Electrical Engineering',
                'year_of_study': 4,
                'batch': '2022 to 2026',
                'address': 'addatheegala, rajahmundry, Andhra Pradesh',
                'parent_contact': '9848054542'
            }
        ]

        for s in students_data:
            user, created = User.objects.get_or_create(
                username=s['username'],
                defaults={
                    'email': s['email'],
                    'role': 'STUDENT',
                    'is_active': True
                }
            )
            if created:
                user.set_password(s['password'])
                user.save()
                
                StudentProfile.objects.create(
                    user=user,
                    full_name=s['full_name'],
                    student_id=s['student_id'],
                    phone=s['phone'],
                    gender=s['gender'],
                    course=s['course'],
                    department=s['department'],
                    year_of_study=s['year_of_study'],
                    batch=s['batch'],
                    address=s['address'],
                    parent_contact=s['parent_contact']
                )
                self.stdout.write(self.style.SUCCESS(f"Student user and profile created for {s['username']}."))
            else:
                self.stdout.write(f"Student user {s['username']} already exists.")
