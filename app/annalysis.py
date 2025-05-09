import pandas as pd
import numpy as np
from django.db.models import Avg
import skfuzzy as fuzz
from django.db import transaction
from .models import Student, AcademicRecord, AttritionAnalysisResult
import logging

logger = logging.getLogger(__name__)

def fetch_student_data():
    students = Student.objects.select_related('course', 'faculty').all()
    data = []

    for student in students:
        records = AcademicRecord.objects.filter(student=student)
        avg_gpa = records.aggregate(Avg('gpa'))['gpa__avg'] or 0

        data.append({
            'student_id': student.id,
            'name': student.first_name,
            'age': student.age,
            'gender': student.gender,
            'faculty': student.faculty.name if student.faculty else None,
            'course': student.course.name if student.course else None,
            'complexity': student.course.complexity if (student.course and hasattr(student.course, 'complexity')) else 'Simple',
            'avg_gpa': avg_gpa,
            'financial_status': student.financial_status,
        })

    return pd.DataFrame(data)

def define_fuzzy_membership_functions():
    gpa_range = np.arange(0, 5.1, 0.1)
    finance_range = np.arange(0, 11, 1)
    complexity_range = np.arange(0, 11, 1)

    return {
        'gpa': {
            'range': gpa_range,
            'low': fuzz.trimf(gpa_range, [0, 0, 2.5]),
            'medium': fuzz.trimf(gpa_range, [2.4, 3.2, 4.0]),
            'high': fuzz.trimf(gpa_range, [3.9, 4.5, 5.0]),
        },
        'finance': {
            'range': finance_range,
            'struggling': fuzz.trimf(finance_range, [0, 0, 3]),
            'good': fuzz.trimf(finance_range, [2, 5, 7]),
            'scholarship': fuzz.trimf(finance_range, [6, 9, 10]),
        },
        'complexity': {
            'range': complexity_range,
            'easy': fuzz.trimf(complexity_range, [0, 0, 3]),
            'moderate': fuzz.trimf(complexity_range, [2, 5, 8]),
            'hard': fuzz.trimf(complexity_range, [7, 10, 10]),
        }
    }

def map_financial_status_to_score(status):
    status = (status or '').strip().lower()
    return {'struggling': 2, 'good': 5, 'scholarship': 8}.get(status, 2)

def map_complexity_to_numeric(complexity_str):
    complexity_str = (complexity_str or '').strip().lower()
    return {'easy': 0, 'moderate': 5, 'hard': 10}.get(complexity_str, 5)

def map_complexity_to_fuzzy_set(level):
    return {'Simple': 'easy', 'Moderate': 'moderate', 'Difficult': 'hard'}.get(level, 'easy')

def compute_risk_for_student(gpa, finance_score, complexity_level, fuzzy_sets):
    if isinstance(complexity_level, str):
        complexity_level = map_complexity_to_numeric(complexity_level)

    gpa_vals = {
        'low': fuzz.interp_membership(fuzzy_sets['gpa']['range'], fuzzy_sets['gpa']['low'], gpa),
        'medium': fuzz.interp_membership(fuzzy_sets['gpa']['range'], fuzzy_sets['gpa']['medium'], gpa),
        'high': fuzz.interp_membership(fuzzy_sets['gpa']['range'], fuzzy_sets['gpa']['high'], gpa),
    }

    finance_vals = {
        'struggling': fuzz.interp_membership(fuzzy_sets['finance']['range'], fuzzy_sets['finance']['struggling'], finance_score),
        'good': fuzz.interp_membership(fuzzy_sets['finance']['range'], fuzzy_sets['finance']['good'], finance_score),
        'scholarship': fuzz.interp_membership(fuzzy_sets['finance']['range'], fuzzy_sets['finance']['scholarship'], finance_score),
    }

    complexity_vals = {
        'easy': fuzz.interp_membership(fuzzy_sets['complexity']['range'], fuzzy_sets['complexity']['easy'], complexity_level),
        'moderate': fuzz.interp_membership(fuzzy_sets['complexity']['range'], fuzzy_sets['complexity']['moderate'], complexity_level),
        'hard': fuzz.interp_membership(fuzzy_sets['complexity']['range'], fuzzy_sets['complexity']['hard'], complexity_level),
    }

    # Weighted risk computation
    high_risk = 0.5 * gpa_vals['low'] + 0.3 * finance_vals['struggling'] + 0.2 * complexity_vals['hard']
    medium_risk = 0.4 * gpa_vals['medium'] + 0.3 * finance_vals['good'] + 0.3 * complexity_vals['moderate']
    low_risk = 0.5 * gpa_vals['high'] + 0.3 * finance_vals['scholarship'] + 0.2 * complexity_vals['easy']

    scores = {'High': high_risk, 'Medium': medium_risk, 'Low': low_risk}
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    risk_level, top_score = sorted_scores[0]
    certainty = int(top_score * 100)

    # Borderline check
    if sorted_scores[0][1] - sorted_scores[1][1] < 0.1:
        alt_level = sorted_scores[1][0]
        risk_level = 'Medium' if 'Medium' in (risk_level, alt_level) else risk_level
        certainty = int((sorted_scores[0][1] + sorted_scores[1][1]) / 2 * 100)

    return risk_level, certainty

def run_attrition_analysis(student=None):
    fuzzy_sets = define_fuzzy_membership_functions()

    try:
        with transaction.atomic():
            if student:
                records = AcademicRecord.objects.filter(student=student)
                avg_gpa = records.aggregate(Avg('gpa'))['gpa__avg'] or 0

                finance_score = map_financial_status_to_score(student.financial_status)
                complexity_level = student.course.complexity if (student.course and hasattr(student.course, 'complexity')) else 'Simple'

                risk_level, certainty = compute_risk_for_student(avg_gpa, finance_score, complexity_level, fuzzy_sets)

                AttritionAnalysisResult.objects.update_or_create(
                    student=student,
                    defaults={'risk_level': risk_level, 'certainty_score': certainty}
                )
                print(f"Analysis for {student.first_name} complete. Risk: {risk_level}, Certainty: {certainty}%")

            else:
                df = fetch_student_data()
                for _, row in df.iterrows():
                    student = Student.objects.get(id=row['student_id'])

                    gpa = row['avg_gpa']
                    finance_score = map_financial_status_to_score(row['financial_status'])
                    complexity_level = row['complexity']

                    risk_level, certainty = compute_risk_for_student(gpa, finance_score, complexity_level, fuzzy_sets)

                    AttritionAnalysisResult.objects.update_or_create(
                        student=student,
                        defaults={'risk_level': risk_level, 'certainty_score': certainty}
                    )
                    print(f"Analysis for {student.first_name} complete. Risk: {risk_level}, Certainty: {certainty}%")

    except Exception as e:
        logger.error(f"Attrition analysis failed: {e}")
        traceback.print_exc()
 
