# Imports
import pandas as pd
import numpy as np
from django.db.models import Avg
import skfuzzy as fuzz  # scikit-fuzzy, used for fuzzy logic computations
from django.db import transaction
from .models import Student, AcademicRecord, AttritionAnalysisResult
import logging
import traceback

logger = logging.getLogger(__name__)  # Configures logger for error reporting

# -----------------------------------------
# Step 1: Data Retrieval
# -----------------------------------------

def fetch_student_data():
    """
    Fetches student data along with their GPA and related metadata (course, faculty, financial status, etc.)
    and returns it as a Pandas DataFrame for easier processing.
    """
    students = Student.objects.select_related('course', 'faculty').all()
    data = []

    for student in students:
        records = AcademicRecord.objects.filter(student=student)
        avg_gpa = records.aggregate(Avg('gpa'))['gpa__avg'] or 0  # Computes average GPA; fallback is 0 if no records

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

    return pd.DataFrame(data)  # Converts list of dicts into DataFrame

# -----------------------------------------
# Step 2: Define Fuzzy Membership Functions
# -----------------------------------------

def define_fuzzy_membership_functions():
    """
    Defines fuzzy membership functions for GPA, financial status, and course complexity.
    Fuzzy logic allows reasoning with degrees of truth rather than fixed binary values.
    """
    gpa_range = np.arange(0, 5.1, 0.1)         # GPA values from 0 to 5
    finance_range = np.arange(0, 11, 1)        # Finance score values from 0 to 10
    complexity_range = np.arange(0, 11, 1)     # Complexity values from 0 to 10

    return {
        'gpa': {
            'range': gpa_range,
            'low': fuzz.trimf(gpa_range, [0, 0, 2.0]),         # Triangular fuzzy set: low GPA
            'medium': fuzz.trimf(gpa_range, [1.8, 3.0, 3.8]),  # Medium GPA
            'high': fuzz.trimf(gpa_range, [3.7, 4.3, 5.0]),    # High GPA
        },
        'finance': {
            'range': finance_range,
            'struggling': fuzz.trimf(finance_range, [0, 0, 3]),       # Poor financial background
            'good': fuzz.trimf(finance_range, [2, 5, 7]),             # Average financial standing
            'scholarship': fuzz.trimf(finance_range, [6, 9, 10]),     # High/Scholarship status
        },
        'complexity': {
            'range': complexity_range,
            'easy': fuzz.trimf(complexity_range, [0, 0, 3]),          # Easy course
            'moderate': fuzz.trimf(complexity_range, [2, 5, 8]),      # Moderate course
            'hard': fuzz.trimf(complexity_range, [7, 10, 10]),        # Difficult course
        }
    }

# -----------------------------------------
# Step 3: Helper Mapping Functions
# -----------------------------------------

def map_financial_status_to_score(status):
    """
    Maps student's financial status string to a numeric score for fuzzy processing.
    Defaults to 'struggling' if status is unknown.
    """
    status = (status or '').strip().lower()
    return {'struggling': 2, 'good': 5, 'scholarship': 8}.get(status, 2)

def map_complexity_to_numeric(complexity_str):
    """
    Converts textual complexity level into numeric values for fuzzy logic.
    """
    complexity_str = (complexity_str or '').strip().lower()
    return {'easy': 0, 'moderate': 5, 'hard': 10}.get(complexity_str, 5)

def map_complexity_to_fuzzy_set(level):
    """
    Maps database-level complexity labels to fuzzy logic set names.
    """
    return {'Simple': 'easy', 'Moderate': 'moderate', 'Difficult': 'hard'}.get(level, 'easy')

# -----------------------------------------
# Step 4: Fuzzy Logic Evaluation
# -----------------------------------------

def compute_risk_for_student(gpa, finance_score, complexity_level, fuzzy_sets):
    """
    Uses fuzzy logic to compute a student's attrition risk level (High, Medium, Low)
    and a certainty score based on GPA, financial score, and course complexity.
    """
    if isinstance(complexity_level, str):
        complexity_level = map_complexity_to_numeric(complexity_level)

    # Membership degrees for GPA
    gpa_vals = {
        'low': fuzz.interp_membership(fuzzy_sets['gpa']['range'], fuzzy_sets['gpa']['low'], gpa),
        'medium': fuzz.interp_membership(fuzzy_sets['gpa']['range'], fuzzy_sets['gpa']['medium'], gpa),
        'high': fuzz.interp_membership(fuzzy_sets['gpa']['range'], fuzzy_sets['gpa']['high'], gpa),
    }

    # Membership degrees for finance
    finance_vals = {
        'struggling': fuzz.interp_membership(fuzzy_sets['finance']['range'], fuzzy_sets['finance']['struggling'], finance_score),
        'good': fuzz.interp_membership(fuzzy_sets['finance']['range'], fuzzy_sets['finance']['good'], finance_score),
        'scholarship': fuzz.interp_membership(fuzzy_sets['finance']['range'], fuzzy_sets['finance']['scholarship'], finance_score),
    }

    # Membership degrees for course complexity
    complexity_vals = {
        'easy': fuzz.interp_membership(fuzzy_sets['complexity']['range'], fuzzy_sets['complexity']['easy'], complexity_level),
        'moderate': fuzz.interp_membership(fuzzy_sets['complexity']['range'], fuzzy_sets['complexity']['moderate'], complexity_level),
        'hard': fuzz.interp_membership(fuzzy_sets['complexity']['range'], fuzzy_sets['complexity']['hard'], complexity_level),
    }

    # Aggregated risk scores using weighted influence of factors
    high_risk = 0.6 * gpa_vals['low'] + 0.25 * finance_vals['struggling'] + 0.15 * complexity_vals['hard']
    medium_risk = 0.4 * gpa_vals['medium'] + 0.3 * finance_vals['good'] + 0.3 * complexity_vals['moderate']
    low_risk = 0.6 * gpa_vals['high'] + 0.25 * finance_vals['scholarship'] + 0.15 * complexity_vals['easy']

    scores = {'High': high_risk, 'Medium': medium_risk, 'Low': low_risk}
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)  # Sort by highest score
    risk_level, top_score = sorted_scores[0]
    certainty = int(top_score * 100)  # Convert to percentage

    # Handle borderline results where two risk levels are very close
    diff = sorted_scores[0][1] - sorted_scores[1][1]
    if diff < 0.12:
        alt = sorted_scores[1][0]
        if 'High' in (risk_level, alt):
            risk_level = 'High'
        elif 'Medium' in (risk_level, alt):
            risk_level = 'Medium'
        certainty = int((sorted_scores[0][1] + sorted_scores[1][1]) / 2 * 100)

    return risk_level, certainty

# -----------------------------------------
# Step 5: Run Analysis for One or All Students
# -----------------------------------------

def run_attrition_analysis(student=None):
    """
    Runs the fuzzy-based attrition risk analysis on:
    - a single student if specified
    - all students if no specific student is passed.
    
    Results are stored in the database (AttritionAnalysisResult).
    """
    fuzzy_sets = define_fuzzy_membership_functions()  # Load fuzzy logic rules

    try:
        with transaction.atomic():  # Ensures DB integrity for batch operations
            if student:
                # Single student analysis
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
                # Batch analysis for all students
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
        traceback.print_exc()  # Logs detailed error trace for debugging

"""
READ ME PLEASE, I AM AN OVERVIEW OF WHAT THIS CODE IS ALL ABOUT
=================================================================================
Attrition Risk Analysis Module - Student Data Evaluation using Fuzzy Logic (FIS)
=================================================================================

OVERVIEW:
---------
This module analyzes student data to predict the **risk of academic attrition** 
(i.e., likelihood of a student dropping out or underperforming academically). 
It uses *Fuzzy Inference Systems (FIS)* to interpret fuzzy variables such as 
GPA, financial status, and course complexity — which are inherently vague and 
not suitable for rigid, rule-based logic.

What is Fuzzy Logic?
--------------------
Fuzzy Logic is a form of many-valued logic that deals with reasoning that is 
approximate rather than fixed and exact. In our context:
- A GPA of 2.8 might be both “low” and “medium” to some degree.
- A financial score might reflect a struggling or stable student.
- Course difficulty might be moderately or highly complex.
Fuzzy logic allows us to assign degrees of membership to these labels and combine 
them to make nuanced predictions about attrition risk.

GOAL:
-----
To classify each student into **High**, **Medium**, or **Low** attrition risk,
and store the result along with a certainty score in the `AttritionAnalysisResult` table.

FLOW & FUNCTION SUMMARY:
------------------------
1. **fetch_student_data()**
   - Loads all students and calculates their average GPA.
   - Also fetches course, faculty, financial status, and course complexity.

2. **define_fuzzy_membership_functions()**
   - Defines fuzzy sets (membership functions) for:
     - GPA: low, medium, high
     - Financial status: struggling, good, scholarship
     - Complexity: easy, moderate, hard
   - These sets are triangular functions defined using `skfuzzy`.

3. **map_financial_status_to_score(status)**
   - Maps textual financial status to a numeric score usable by the FIS.

4. **map_complexity_to_numeric(complexity_str)**
   - Converts course complexity string to a numeric scale [0–10].

5. **map_complexity_to_fuzzy_set(level)**
   - Maps stored course complexity values (Simple, Moderate, Difficult)
     to fuzzy variable labels (easy, moderate, hard).

6. **compute_risk_for_student(gpa, finance_score, complexity_level, fuzzy_sets)**
   - Calculates degrees of membership for each input using `interp_membership`.
   - Applies weighted rules to calculate High, Medium, and Low risk scores.
   - Selects the risk category with the highest confidence score.
   - If two values are close (borderline), applies adjusted logic for more nuance.
   - Returns the most probable **risk level** and its **certainty percentage**.

7. **run_attrition_analysis(student=None)**
   - Main orchestrator function.
   - If a specific student is passed, analyzes that student only.
   - Otherwise, runs analysis for all students.
   - Each result is saved or updated in the `AttritionAnalysisResult` table.
   - Uses atomic transactions to ensure database integrity.
   - Exceptions are logged for review.

EXAMPLE:
--------
A student with:
    - GPA = 2.4 (medium/low),
    - Financial status = 'good' (score = 5),
    - Complexity = 'Moderate' (mapped to 5),
    
...will be fuzzified into:
    - GPA → partial membership in "low" and "medium"
    - Finance → membership in "good"
    - Complexity → membership in "moderate"
    
The FIS combines these using weighted rules to decide the likely **risk level**.

USAGE NOTES:
------------
- This logic supports both batch and individual student analysis.
- The certainty score (e.g., 82%) helps identify borderline predictions.
- Designed to be extended — more features like attendance or mental health score
  could be added as new fuzzy input variables in the future.
"""
