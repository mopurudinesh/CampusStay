from django.db import migrations

def populate_blocks(apps, schema_editor):
    HostelBlock = apps.get_model('hostel', 'HostelBlock')
    HostelBlock.objects.get_or_create(name="Block A", description="Main Boys Hostel Block")
    HostelBlock.objects.get_or_create(name="Block B", description="Main Girls Hostel Block")
    HostelBlock.objects.get_or_create(name="Block C", description="International Hostel Block")

class Migration(migrations.Migration):

    dependencies = [
        ('hostel', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(populate_blocks),
    ]
