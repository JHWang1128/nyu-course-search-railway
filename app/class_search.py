"""
NYU Class Search API Client

Fetches live class schedule data from NYU's bulletins.nyu.edu Class Search API.
"""

import httpx
from typing import Optional
import json

# NYU Class Search API endpoint
CLASS_SEARCH_API = "https://bulletins.nyu.edu/class-search/api/"

# Term codes - ordered from most recent to oldest (only back to 2024)
# Format: {"code": "1264", "name": "Spring 2026"}
TERM_CODES = [
    {"code": "1266", "name": "Summer 2026"},
    {"code": "1264", "name": "Spring 2026"},
    {"code": "1262", "name": "January 2026"},
    {"code": "1258", "name": "Fall 2025"},
    {"code": "1256", "name": "Summer 2025"},
    {"code": "1254", "name": "Spring 2025"},
    {"code": "1252", "name": "January 2025"},
    {"code": "1248", "name": "Fall 2024"},
    {"code": "1246", "name": "Summer 2024"},
    {"code": "1244", "name": "Spring 2024"},
]


async def fetch_class_sections(course_code: str, term_code: str) -> dict:
    """
    Fetch class sections for a given course code and term.
    
    Args:
        course_code: The course code (e.g., "CSCI-UA 473")
        term_code: The term code (e.g., "1264" for Spring 2026)
    
    Returns:
        dict with classes data or error
    """
    # Build API request payload
    payload = {
        "other": {"srcdb": term_code},
        "criteria": [{"field": "keyword", "value": course_code}]
    }
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{CLASS_SEARCH_API}?page=fose&route=search",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for API errors
                if "fatal" in data:
                    return {"error": data["fatal"]}
                
                return {
                    "term_code": term_code,
                    "count": data.get("count", 0),
                    "results": data.get("results", [])
                }
            else:
                return {"error": f"API returned {response.status_code}"}
                
    except httpx.TimeoutException:
        return {"error": "Request timed out"}
    except Exception as e:
        return {"error": str(e)}


async def fetch_class_sections_multi_term(course_code: str) -> dict:
    """
    Fetch class sections, searching from current term backwards until 2024.
    Returns the first term that has matching classes.
    """
    for term in TERM_CODES:
        result = await fetch_class_sections(course_code, term["code"])
        
        if result.get("error"):
            continue
            
        if result.get("count", 0) > 0:
            # Found classes in this term
            return {
                "term_code": term["code"],
                "term_name": term["name"],
                "count": result["count"],
                "classes": result["results"]
            }
    
    # No classes found in any term back to 2024
    return {
        "classes": [],
        "count": 0,
        "message": "This course has not been offered since Spring 2024."
    }


def get_term_name(code: str) -> str:
    """Get human-readable term name from code."""
    for term in TERM_CODES:
        if term["code"] == code:
            return term["name"]
    return f"Term {code}"


def format_class_for_display(class_data: dict) -> dict:
    """Format a class section for frontend display."""
    # Parse meeting times if available
    meets = class_data.get("meets", "TBA")
    
    # Map schedule type codes
    schd_map = {
        "LEC": "Lecture",
        "RCT": "Recitation",
        "LAB": "Lab",
        "SEM": "Seminar",
        "IND": "Independent Study",
        "CLI": "Clinic",
        "STU": "Studio",
    }
    schd_code = class_data.get("schd", "")
    schd_name = schd_map.get(schd_code, schd_code)
    
    # Map status codes
    status_map = {
        "A": "Open",
        "C": "Closed",
        "W": "Waitlist",
        "X": "Cancelled",
    }
    stat_code = class_data.get("stat", "")
    status = status_map.get(stat_code, stat_code)
    
    return {
        "section": class_data.get("no", ""),
        "crn": class_data.get("crn", ""),
        "type": schd_name,
        "status": status,
        "instructor": class_data.get("instr", "Staff") or "Staff",
        "schedule": meets,
        "start_date": class_data.get("start_date", ""),
        "end_date": class_data.get("end_date", ""),
        "credits": class_data.get("total", ""),
        "is_cancelled": class_data.get("isCancelled", "") == "Y",
    }
