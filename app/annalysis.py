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
 

def run_attrition_analysis():
    """
    Fetches data, applies fuzzy logic, and saves results.
    This function calls the fatch_students_data function and stores
    its contained data fram into a varriable df, making students data ready 
    to be worked on by data manupulation function from pandas or numpy ,etc
    """
    # 1. Fetch data
    df = fetch_student_data()
    print(f"Total students fetched: {len(df)}")

    pass
 
 
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




def run_attrition_analysis(chunk_size=10):
    """
    Main function to fetch student data, run fuzzy analysis,
    and save risk results to the database, processing in chunks.
    Optimized to reduce memory usage and handle batch updates.
    """
    print("🚀 Initializing attrition analysis...")

    # Load student data efficiently
    student_df = fetch_student_data()
    if student_df.empty:
        print("⚠️ No student data found. Exiting analysis.")
        return

    total_students = len(student_df)
    fuzzy_sets = define_fuzzy_membership_functions()

    print(f"🚀 Starting attrition analysis for {total_students} students in chunks of {chunk_size}...")

    for start in range(0, total_students, chunk_size):
        end = min(start + chunk_size, total_students)
        chunk = student_df.iloc[start:end]
        print(f"\n📦 Processing students {start + 1} to {end}...")

        results_to_update = []
        missing_students = []
        skipped_students = []

        for index, row in chunk.iterrows():
            try:
                student_id = row.get('student_id')
                gpa = row.get('avg_gpa')
                finance_status = row.get('financial_status')
                complexity_level = row.get('complexity')

                # Basic data validation
                if student_id is None or gpa is None or finance_status is None or complexity_level is None:
                    print(f"⚠️ Skipping student at index {index} due to missing fields.")
                    skipped_students.append(student_id)
                    continue

                finance_score = map_financial_status_to_score(finance_status)

                risk_level, certainty = compute_risk_for_student(
                    gpa, finance_score, complexity_level, fuzzy_sets
                )

                student = Student.objects.filter(id=student_id).first()
                if not student:
                    missing_students.append(student_id)
                    continue

                result = AttritionAnalysisResult(
                    student=student,
                    risk_level=risk_level,
                    certainty_score=certainty
                )
                results_to_update.append(result)

            except Exception as e:
                print(f"❌ Error processing student ID {row.get('student_id')} at index {index}: {e}")
                traceback.print_exc()

        if results_to_update:
            try:
                with transaction.atomic():
                    AttritionAnalysisResult.objects.bulk_update_or_create(
                        results_to_update,
                        ['risk_level', 'certainty_score'],
                        match_field='student'
                    )
                print(f"✅ Saved {len(results_to_update)} analysis results.")
            except Exception as db_error:
                print(f"❌ DB error during bulk update: {db_error}")
                traceback.print_exc()

        if missing_students:
            print(f"⚠️ {len(missing_students)} students not found in DB: {missing_students}")
        if skipped_students:
            print(f"⚠️ {len(skipped_students)} students skipped due to missing fields: {skipped_students}")

        # Optional: monitor memory usage
        print(f"📊 Memory usage: {psutil.Process().memory_info().rss / 1024 ** 2:.2f} MB")

    print("\n🎉 All chunks processed. Attrition analysis completed.")
