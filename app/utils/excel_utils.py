import pandas as pd
import os
from typing import List, Dict

def parse_exam_questions(file_path: str) -> Dict:
    """
    Parses an Excel file where each sheet is a section.
    Returns: {
        "sections": [
            {"name": "Maths", "questions": [...]}
        ],
        "total_questions": 100
    }
    """
    if not os.path.exists(file_path):
        return {"sections": [], "total_questions": 0}
    
    excel_data = pd.read_excel(file_path, sheet_name=None)
    sections = []
    total_q = 0
    
    for sheet_name, df in excel_data.items():
        # Ensure required columns exist
        required_cols = ['Question', 'Option A', 'Option B', 'Option C', 'Option D', 'Correct Answer']
        if not all(col in df.columns for col in required_cols):
            continue
            
        questions = []
        for index, row in df.iterrows():
            if pd.isna(row['Question']): continue
            
            questions.append({
                "id": f"{sheet_name}_{index}",
                "text": str(row['Question']),
                "options": {
                    "A": str(row['Option A']),
                    "B": str(row['Option B']),
                    "C": str(row['Option C']),
                    "D": str(row['Option D'])
                },
                "correct": str(row['Correct Answer']).strip().upper().replace("OPTION ", "")
            })
            total_q += 1
            
        sections.append({
            "name": sheet_name,
            "questions": questions,
            "count": len(questions)
        })
        
    return {
        "sections": sections,
        "total_questions": total_q
    }
