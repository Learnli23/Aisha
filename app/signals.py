from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Student, AcademicRecord
import datetime

@receiver(post_save, sender=Student)
def create_or_update_academic_record_for_student(sender, instance, created, **kwargs):
    current_year = datetime.datetime.now().year

    if created:
        # When a new student is created, also create a new academic record
        AcademicRecord.objects.create(
            student=instance,
            gpa=instance.gpa,
            year=current_year,
            notes='Initial record from student creation'
        )
        print(f"Created AcademicRecord for {instance.first_name} {instance.last_name} (GPA: {instance.gpa})")
    else:
        try:
            academic_record = AcademicRecord.objects.get(student=instance, year=current_year)
            if academic_record.gpa != instance.gpa:
                old_gpa = academic_record.gpa
                academic_record.gpa = instance.gpa
                academic_record.save()
                print(f"Updated GPA for {instance.first_name} {instance.last_name} from {old_gpa} to {instance.gpa}")
        except AcademicRecord.DoesNotExist:
            # If no record exists, create one
            AcademicRecord.objects.create(
                student=instance,
                gpa=instance.gpa,
                year=current_year,
                notes='Auto-created record due to missing academic record'
            )
            print(f"Auto-created missing AcademicRecord for {instance.first_name} {instance.last_name} (GPA: {instance.gpa})")