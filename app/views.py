from django.shortcuts import render
from django.shortcuts import render, redirect
from django.contrib import messages
from .annalysis import run_attrition_analysis
from .models import AttritionAnalysisResult,AcademicRecord
from .models import Student
from django.db import models
import traceback
from threading import Thread
import threading
from django.contrib.auth import authenticate, login
from .forms import AdminLoginForm
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
 
 
 # Create your views here.
def home(request):
    return render(request,'home.html')

# REGISTER USER
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm

def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()  # Save the new user
            login(request, user)  # Automatically log in the user
            return redirect('home')  # Redirect to homepage (replace 'home' with your URL name)
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})

 
def trigger_analysis(request):
    if request.method == 'POST':
        try:
            run_attrition_analysis()
            messages.success(request, '✅ Student attrition analysis has been completed.')
        except Exception as e:
            traceback.print_exc()
            messages.error(request, f'❌ An error occurred during analysis: {str(e)}')
        return redirect('view_analysis_results')
    
    return render(request, 'trigger_analysis.html')
  


def admin_login(request):
    if request.method == 'POST':
        form = AdminLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None and user.is_superuser:  # restrict to admin/staff users
                login(request, user)
                return redirect('home')  # replace with your actual dashboard view
            else:
                messages.error(request, 'Invalid credentials or not authorized')
    else:
        form = AdminLoginForm()
    return render(request, 'admin_login.html', {'form': form})
 

@login_required
def view_analysis_results(request):
    if request.method == 'POST':
        run_attrition_analysis()  # Run for all students
        messages.success(request, 'Attrition analysis updated for all students.')
        return redirect('view_analysis_results')

    results = AttritionAnalysisResult.objects.select_related('student').all()
    return render(request, 'view_analysis_results.html', {'results': results})


@login_required 
def dashboard_view(request):
    total_students = Student.objects.count()  # counts all students
    # Students per Academic Year (assuming academic_year values are like 1,2,3,4)
    students_per_year = (
        Student.objects.values('academic_year')
        .order_by('academic_year')
        .annotate(count=models.Count('id'))
    )
    # styudents per gender
    gender_data = Student.objects.values('gender').annotate(count=models.Count('id'))
    genders = [item['gender'] for item in gender_data]
    gender_counts = [item['count'] for item in gender_data]

   # Students per faculty (getting faculty names)
    faculty_data = Student.objects.values('faculty__name').annotate(count=models.Count('id'))
    faculties = [entry['faculty__name'] for entry in faculty_data]
    faculty_counts = [entry['count'] for entry in faculty_data]

    # Students per course (getting course names)
    course_data = Student.objects.values('course__name').annotate(count=models.Count('id'))
    courses = [entry['course__name'] for entry in course_data]
    course_counts = [entry['count'] for entry in course_data]
   
   
   
    context = {
        'total_students': total_students,
        'students_per_year': students_per_year,
        'genders': genders,
        'gender_counts': gender_counts,
        'faculties': faculties,
        'faculty_counts': faculty_counts,
        'courses': courses,
        'course_counts': course_counts,
    }
    return render(request, 'dashboard.html', context)  

@login_required
def risk_level_distribution(request):
    risk_data =AttritionAnalysisResult.objects.values('risk_level').annotate(count=models.Count('id'))

    # Prepare data for Chart.js
    labels = []
    counts = []
    for entry in risk_data:
        labels.append(entry['risk_level'])  # e.g., 'Low', 'Medium', 'High'
        counts.append(entry['count'])

 
     # Faculties with high risk
    faculty_risk =  AttritionAnalysisResult.objects.filter(risk_level='High').values('student__faculty__name').annotate(count=models.Count('id'))

    # Years with high risk
    year_risk = AttritionAnalysisResult.objects.filter(risk_level='High').values('student__academic_year').annotate(count=models.Count('id'))

    # Courses with high risk
    course_risk = AttritionAnalysisResult.objects.filter(risk_level='High').values('student__course__name').annotate(count=models.Count('id'))

    # Genders with high risk
    gender_risk = AttritionAnalysisResult.objects.filter(risk_level='High').values('student__gender').annotate(count=models.Count('id'))
    # Organizing data to pass to the template
    # Preparing lists
    faculty_labels = [entry['student__faculty__name'] for entry in faculty_risk]
    faculty_counts = [entry['count'] for entry in faculty_risk]

    year_labels = [entry['student__academic_year'] for entry in year_risk]
    year_counts = [entry['count'] for entry in year_risk]

    course_labels = [entry['student__course__name'] for entry in course_risk]
    course_counts = [entry['count'] for entry in course_risk]

    gender_labels = [entry['student__gender'] for entry in gender_risk]
    gender_counts = [entry['count'] for entry in gender_risk]

    context = {
        'labels': labels,
        'counts': counts,
        'faculty_labels': faculty_labels,
        'faculty_counts': faculty_counts,
        'year_labels': year_labels,
        'year_counts': year_counts,
        'course_labels': course_labels,
        'course_counts': course_counts,
        'gender_labels': gender_labels,
        'gender_counts': gender_counts,
    }
    return render(request, 'attrition_dashboard.html', context)
