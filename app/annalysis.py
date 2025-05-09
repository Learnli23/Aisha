import pandas as pd
import numpy as np
from django.db.models import Avg
import skfuzzy as fuzz
from django.db import transaction
import traceback
import psutil
from django.db.models import F
from .models import Student, AcademicRecord, AttritionAnalysisResult
import logging
logger = logging.getLogger(__name__)

def fetch_student_data():
    students = Student.objects.select_related('course', 'faculty').all()

    data = []
    for student in students:
        records = AcademicRecord.objects.filter(student=student)
        avg_gpa = records.aggregate(Avg('gpa'))['gpa__avg'] if records.exists() else 0

        data.append({
            'student_id': student.id,
            'name': student.first_name,
            'age': student.age,
            'gender': student.gender,
            'faculty': student.faculty.name if student.faculty else None,
            'course': student.course.name if student.course else None,
            'complexity': student.course.complexity if (student.course and hasattr(student.course, 'complexity')) else 'Simple',  # Default 'Simple'
            'avg_gpa': avg_gpa,
            'financial_status': student.financial_status,
        })

    df = pd.DataFrame(data)
    return df

# Defining Fuzzy Membership Functions 
def define_fuzzy_membership_functions():
    # GPA (0–5 scale)
    gpa_range = np.arange(0, 5.1, 0.1)
    gpa_low = fuzz.trimf(gpa_range, [0, 0, 2.5])
    gpa_medium = fuzz.trimf(gpa_range, [2.4, 3.2, 4.0])
    gpa_high = fuzz.trimf(gpa_range, [3.9, 4.5, 5.0])

    # Financial status scores (0–10)
    finance_range = np.arange(0, 11, 1)
    finance_struggling = fuzz.trimf(finance_range, [0, 0, 3])
    finance_good = fuzz.trimf(finance_range, [2, 5, 7])
    finance_scholarship = fuzz.trimf(finance_range, [6, 9, 10])

    # Course complexity (0–10)
    complexity_range = np.arange(0, 11, 1)
    complexity_easy = fuzz.trimf(complexity_range, [0, 0, 3])
    complexity_moderate = fuzz.trimf(complexity_range, [2, 5, 8])
    complexity_hard = fuzz.trimf(complexity_range, [7, 10, 10])

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

# application of fuzzy logic to data
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
        return 2  # Default to 'struggling'

def map_complexity_to_fuzzy_set(complexity_level):
    """
    Maps course complexity levels to fuzzy sets.
    """
    complexity_mapping = {
        'Simple': 'easy',
        'Moderate': 'moderate',
        'Difficult': 'hard',
    }
    return complexity_mapping.get(complexity_level, 'easy')  # Default to 'easy'
def map_complexity_to_numeric(complexity_str):
    """
    Maps course complexity string to a numeric value.
    """
    if complexity_str == 'easy':
        return 0
    elif complexity_str == 'moderate':
        return 5
    elif complexity_str == 'hard':
        return 10
    else:
        return 5  # Default to 'moderate' if unknown

def compute_risk_for_student(gpa, finance_score, complexity_level, fuzzy_sets):
    if isinstance(complexity_level, str):
        complexity_level = map_complexity_to_numeric(complexity_level)

    # Fuzzy memberships
    gpa_vals = {
        'low': fuzz.interp_membership(fuzzy_sets['gpa']['range'], fuzzy_sets['gpa']['low'], gpa),
        'medium': fuzz.interp_membership(fuzzy_sets['gpa']['range'], fuzzy_sets['gpa']['medium'], gpa),
        'high': fuzz.interp_membership(fuzzy_sets['gpa']['range'], fuzzy_sets['gpa']['high'], gpa)
    }

    finance_vals = {
        'struggling': fuzz.interp_membership(fuzzy_sets['finance']['range'], fuzzy_sets['finance']['struggling'], finance_score),
        'good': fuzz.interp_membership(fuzzy_sets['finance']['range'], fuzzy_sets['finance']['good'], finance_score),
        'scholarship': fuzz.interp_membership(fuzzy_sets['finance']['range'], fuzzy_sets['finance']['scholarship'], finance_score)
    }

    complexity_vals = {
        'easy': fuzz.interp_membership(fuzzy_sets['complexity']['range'], fuzzy_sets['complexity']['easy'], complexity_level),
        'moderate': fuzz.interp_membership(fuzzy_sets['complexity']['range'], fuzzy_sets['complexity']['moderate'], complexity_level),
        'hard': fuzz.interp_membership(fuzzy_sets['complexity']['range'], fuzzy_sets['complexity']['hard'], complexity_level)
    }

    # Risk scoring using weighted rule base
    high_risk_score = (
        0.5 * gpa_vals['low'] +
        0.3 * finance_vals['struggling'] +
        0.2 * complexity_vals['hard']
    )

    medium_risk_score = (
        0.4 * gpa_vals['medium'] +
        0.3 * finance_vals['good'] +
        0.3 * complexity_vals['moderate']
    )

    low_risk_score = (
        0.5 * gpa_vals['high'] +
        0.3 * finance_vals['scholarship'] +
        0.2 * complexity_vals['easy']
    )

    # Decision based on maximum and borderline threshold
    scores = {
        'High': high_risk_score,
        'Medium': medium_risk_score,
        'Low': low_risk_score
    }
    risk_level = max(scores, key=scores.get)
    certainty = int(scores[risk_level] * 100)

    # Borderline adjustment
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    if sorted_scores[0][1] - sorted_scores[1][1] < 0.1:
        risk_level = 'Medium' if 'Medium' in [sorted_scores[0][0], sorted_scores[1][0]] else sorted_scores[0][0]
        certainty = int((sorted_scores[0][1] + sorted_scores[1][1]) / 2 * 100)

    return risk_level, certainty

def run_attrition_analysis(student=None):
    """
    Run fuzzy attrition analysis. If a student is provided, analyze that student only.
    """
    fuzzy_sets = define_fuzzy_membership_functions()

    if student:
        records = AcademicRecord.objects.filter(student=student)
        avg_gpa = records.aggregate(Avg('gpa'))['gpa__avg'] if records.exists() else 0

        row = {
            'student_id': student.id,
            'avg_gpa': avg_gpa,
            'financial_status': student.financial_status,
            'complexity': student.course.complexity if (student.course and hasattr(student.course, 'complexity')) else 'Simple'  # Default 'Simple'
        }

        gpa = row['avg_gpa']
        finance_score = map_financial_status_to_score(row['financial_status'])
        complexity_level = row['complexity']

        risk_level, certainty = compute_risk_for_student(gpa, finance_score, complexity_level, fuzzy_sets)

        analysis_result, created = AttritionAnalysisResult.objects.update_or_create(
            student=student,
            defaults={
                'risk_level': risk_level,
                'certainty_score': certainty,
            }
        )

        print(f"{'Created' if created else 'Updated'} analysis for {student.first_name}")

    else:
        # Original logic
        student_df = fetch_student_data()

        for index, row in student_df.iterrows():
            gpa = row['avg_gpa']
            finance_score = map_financial_status_to_score(row['financial_status'])
            complexity_level = row['complexity']

            risk_level, certainty = compute_risk_for_student(gpa, finance_score, complexity_level, fuzzy_sets)

            student = Student.objects.get(id=row['student_id'])
            analysis_result, created = AttritionAnalysisResult.objects.update_or_create(
                student=student,
                defaults={
                    'risk_level': risk_level,
                    'certainty_score': certainty,
                }
            )

            print(f"{'Created' if created else 'Updated'} analysis for {student.first_name}")
 
