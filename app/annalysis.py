import pandas as pd
import numpy as np
from django.db.models import Avg
import skfuzzy as fuzz
from django.db import transaction
import traceback
import psutil
from django.db.models import F
from .models import Student, AcademicRecord, AttritionAnalysisResult
 

def fetch_student_data():
    students = Student.objects.select_related('course', 'faculty').all()

    data = []
    for student in students:
        records = AcademicRecord.objects.filter(student=student)
        avg_gpa = records.aggregate(Avg('gpa'))['gpa__avg'] if records.exists() else 0

        data.append({
            'student_id': student.id,
            'name': student.first_name ,
            'age': student.age,
            'gender': student.gender,
            'faculty': student.faculty.name if student.faculty else None,
            'course': student.course.name if student.course else None,
            'complexity': student.course.complexity if (student.course and hasattr(student.course, 'complexity')) else 5,  # DEFAULT 5
            'avg_gpa': avg_gpa,
            'financial_status': student.financial_status,
        })

    df = pd.DataFrame(data)
    return df
  
#Defining Fuzzy Membership Functions 
def define_fuzzy_membership_functions():
    """
    Define fuzzy membership functions for GPA, Financial Status, and Course Complexity.
    Returns dictionaries of fuzzy variables.
    """
    # GPA
    gpa_range = np.arange(0, 4.1, 0.1)
    gpa_low = fuzz.trimf(gpa_range, [0, 0, 2])
    gpa_medium = fuzz.trimf(gpa_range, [1.5, 2.5, 3.5])
    gpa_high = fuzz.trimf(gpa_range, [3.0, 4.0, 4.0])

    # Financial status (we assign scores: struggling = 2, good = 5, scholarship = 8)
    finance_range = np.arange(0, 11, 1)
    finance_struggling = fuzz.trimf(finance_range, [0, 0, 4])
    finance_good = fuzz.trimf(finance_range, [3, 5, 7])
    finance_scholarship = fuzz.trimf(finance_range, [6, 10, 10])

    # Course complexity (0=Easy, 10=Hard)
    complexity_range = np.arange(0, 11, 1)
    complexity_easy = fuzz.trimf(complexity_range, [0, 0, 4])
    complexity_moderate = fuzz.trimf(complexity_range, [3, 5, 7])
    complexity_hard = fuzz.trimf(complexity_range, [6, 10, 10])

    return {
        'gpa': {
            'range': gpa_range,
            'low': gpa_low,
            'medium': gpa_medium,
            'high': gpa_high,
        },
        'finance': {
            'range': finance_range,
            'struggling': finance_struggling,
            'good': finance_good,
            'scholarship': finance_scholarship,
        },
        'complexity': {
            'range': complexity_range,
            'easy': complexity_easy,
            'moderate': complexity_moderate,
            'hard': complexity_hard,
        }
    }



'''
Summary:
GPA will be classified as Low, Medium, High based on thresholds.
Financial status is also converted into a numeric form internally.
Course complexity is mapped to Easy, Moderate, Hard.
'''

# application of fizzy logic to data
def map_financial_status_to_score(status):
    """
    Maps financial status string to a numeric score.
    """
    status = status.lower()
    if status == 'struggling':
        return 2
    elif status == 'good':
        return 5
    elif status == 'scholarship':
        return 8
    else:
        return 2  # Assume 'struggling' if unknown

def compute_risk_for_student(gpa, finance_score, complexity_level, fuzzy_sets):
    """
    Given a student's parameters and fuzzy membership functions,
.
calculate risk level and certainty score.
    """

    # Membership degrees
    gpa_low = fuzz.interp_membership(fuzzy_sets['gpa']['range'], fuzzy_sets['gpa']['low'], gpa)
    gpa_medium = fuzz.interp_membership(fuzzy_sets['gpa']['range'], fuzzy_sets['gpa']['medium'], gpa)
    gpa_high = fuzz.interp_membership(fuzzy_sets['gpa']['range'], fuzzy_sets['gpa']['high'], gpa)

    finance_struggling = fuzz.interp_membership(fuzzy_sets['finance']['range'], fuzzy_sets['finance']['struggling'], finance_score)
    finance_good = fuzz.interp_membership(fuzzy_sets['finance']['range'], fuzzy_sets['finance']['good'], finance_score)
    finance_scholarship = fuzz.interp_membership(fuzzy_sets['finance']['range'], fuzzy_sets['finance']['scholarship'], finance_score)

    complexity_easy = fuzz.interp_membership(fuzzy_sets['complexity']['range'], fuzzy_sets['complexity']['easy'], complexity_level)
    complexity_moderate = fuzz.interp_membership(fuzzy_sets['complexity']['range'], fuzzy_sets['complexity']['moderate'], complexity_level)
    complexity_hard = fuzz.interp_membership(fuzzy_sets['complexity']['range'], fuzzy_sets['complexity']['hard'], complexity_level)

    # Fuzzy rules 
    high_risk = max(
        gpa_low,
        finance_struggling,
        complexity_hard
    )
    medium_risk = max(
        gpa_medium,
        finance_good,
        complexity_moderate
    )
    low_risk = max(
        gpa_high,
        finance_scholarship,
        complexity_easy
    )

    # Decide final Risk Level
    if high_risk >= medium_risk and high_risk >= low_risk:
        risk_level = 'High'
        certainty = int(high_risk * 100)
    elif medium_risk >= low_risk:
        risk_level = 'Medium'
        certainty = int(medium_risk * 100)
    else:
        risk_level = 'Low'
        certainty = int(low_risk * 100)

    return risk_level, certainty


def run_attrition_analysis():
    """
    Main function to fetch student data, run fuzzy analysis,
    and save risk results to the database.
    """
    # Load student data
    student_df = fetch_student_data()

    # Setup fuzzy logic
    fuzzy_sets = define_fuzzy_membership_functions()

    # Loop through each student
    for index, row in student_df.iterrows():
        # Prepare input variables
        gpa = row['avg_gpa']
        finance_score = map_financial_status_to_score(row['financial_status'])
        complexity_level = row['complexity']

        # Run fuzzy logic computation
        risk_level, certainty = compute_risk_for_student(
            gpa, finance_score, complexity_level, fuzzy_sets
        )

        # Save or update analysis result
        student = Student.objects.get(id=row['student_id'])
        analysis_result, created = AttritionAnalysisResult.objects.update_or_create(
            student=student,
            defaults={
                'risk_level': risk_level,
                'certainty_score': certainty,
            }
        )

        if created:
            print(f"Created analysis for {student.first_name}")
        else:
            print(f"Updated analysis for {student.first_name}")

