from django.db import models

# Create your models here.
# 1. Faculty Model this model will store all infomation about the faculty
class Faculty(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

# 2. Course Model, stores all ninformation about the course
class Course(models.Model):
    name = models.CharField(max_length=100)
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE)
   
    # Complexity choices
    SIMPLE = 'Simple'
    MODERATE = 'Moderate'
    DIFFICULT = 'Difficult'
    COMPLEXITY_CHOICES = [
        (SIMPLE, 'Simple'),
        (MODERATE, 'Moderate'),
        (DIFFICULT, 'Difficult'),
    ]
    complexity_level = models.CharField(max_length=10, choices=COMPLEXITY_CHOICES, default=SIMPLE)

    def __str__(self):
        return self.name

# 3. Student Model
class Student(models.Model):
    # Gender choices
    MALE = 'Male'
    FEMALE = 'Female'
    GENDER_CHOICES = [
        (MALE, 'Male'),
        (FEMALE, 'Female'),
        
    ]

    # Financial status choices
    GOOD = 'Good'
    STRUGGLING = 'Struggling'
    SCHOLARSHIP = 'Scholarship'
    FINANCIAL_STATUS_CHOICES = [
        (GOOD, 'Good'),
        (STRUGGLING, 'Struggling'),
        (SCHOLARSHIP, 'Scholarship'),
    ]

    # Enrollment status
    ACTIVE = 'Active'
    DROPPED_OUT = 'Dropped Out'
    GRADUATED = 'Graduated'
    ENROLLMENT_STATUS_CHOICES = [
        (ACTIVE, 'Active'),
        (DROPPED_OUT, 'Dropped Out'),
        (GRADUATED, 'Graduated'),
    ]

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    age = models.PositiveIntegerField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    academic_year = models.PositiveIntegerField()
    financial_status = models.CharField(max_length=15, choices=FINANCIAL_STATUS_CHOICES, default=GOOD)
    enrollment_status = models.CharField(max_length=15, choices=ENROLLMENT_STATUS_CHOICES, default=ACTIVE)
    gpa = models.FloatField(default=1.0)  # GPA added here
    def __str__(self):
        return f"{self.first_name} {self.last_name}"

# 4. Academic Record Model
class AcademicRecord(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='academic_records')
    gpa = models.FloatField()  # GPA or average grade
    year = models.PositiveIntegerField()
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Record for {self.student.first_name} {self.student.last_name} - Year {self.year}"

# 5. Attrition Analysis Result Model
class AttritionAnalysisResult(models.Model):
    # Risk levels
    LOW = 'Low'
    MEDIUM = 'Medium'
    HIGH = 'High'
    CRITICAL = 'Critical'
    RISK_LEVEL_CHOICES = [
        (LOW, 'Low'),
        (MEDIUM, 'Medium'),
        (HIGH, 'High'),
        (CRITICAL, 'Critical'),
    ]

    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='attrition_result')
    risk_level = models.CharField(max_length=10, choices=RISK_LEVEL_CHOICES)
    reason = models.TextField(blank=True)
    certainty_score = models.FloatField(help_text="Certainty percentage between 0 and 100.")

    def __str__(self):
        return f"Risk Analysis for {self.student.first_name} {self.student.last_name}"

'''
Summary of What This Code Does
Faculty and Course are linked.
Student is linked to Faculty and Course.
Student has multiple AcademicRecords (one for each academic year).
Student has one AttritionAnalysisResult (one-to-one link).
Choices fields (dropdowns) are used for controlled inputs like gender, financial status, risk level, etc.
Easy __str__ methods for better display in admin panel.
 
'''

