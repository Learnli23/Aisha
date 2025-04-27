from django.contrib import admin
# Register your models here.
from django.contrib import admin
from .models import Faculty, Course, Student, AcademicRecord, AttritionAnalysisResult

# Faculty Admin
@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

# Course Admin
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'faculty', 'complexity_level')
    list_filter = ('faculty', 'complexity_level')
    search_fields = ('name',)

# Student Admin
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'faculty', 'course', 'academic_year', 'enrollment_status')
    list_filter = ('faculty', 'course', 'academic_year', 'enrollment_status', 'financial_status', 'gender')
    search_fields = ('first_name', 'last_name')
    autocomplete_fields = ['faculty', 'course']

# Academic Record Admin
@admin.register(AcademicRecord)
class AcademicRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'gpa', 'year')
    list_filter = ('year',)
    search_fields = ('student__first_name', 'student__last_name')
    autocomplete_fields = ['student']

# Attrition Analysis Result Admin
@admin.register(AttritionAnalysisResult)
class AttritionAnalysisResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'risk_level', 'certainty_score')
    list_filter = ('risk_level',)
    search_fields = ('student__first_name', 'student__last_name')
    autocomplete_fields = ['student']
    
'''
What This Admin Setup Does:
It makes all models manageable in Django Admin.
It shows useful columns in the admin tables.
Adds filters (by faculty, course, risk level, etc.).
Adds search by student names.
Uses autocomplete fields where there are ForeignKeys (for better performance).
 
'''    


