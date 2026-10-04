"""The tools the harness can run, and the JSON that describes them to the model."""

import json
import requests
from datetime import datetime, timedelta, timezone
import re

from io import BytesIO
from bs4 import BeautifulSoup
from docx import Document
from pypdf import PdfReader

from flask import session
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from zoneinfo import ZoneInfo

import os

CANVAS_TOKEN = os.getenv("CANVAS_TOKEN")

CANVAS_URL = "https://courseworks2.columbia.edu"

HEADERS = {
    "Authorization": f"Bearer {CANVAS_TOKEN}"
}

# api keys (to be removed)
#CANVAS_TOKEN = "1396~vvT99B87vKyPE6yxtDzU8EBhkkJhVmhNr2QHCJEaLG7QE9fE8tW9rXKCLR9r3RCk"

# define url used
CANVAS_URL = "https://courseworks2.columbia.edu"
HEADERS = {
    "Authorization": f"Bearer {CANVAS_TOKEN}"
}

def clean_html(html):
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text("\n", strip=True)


def download_canvas_file(file):
    response = requests.get(
        file["url"],
        headers=HEADERS,
        timeout=20,
    )

    response.raise_for_status()
    return response.content


def read_word_file(file):
    content = download_canvas_file(file)

    document = Document(BytesIO(content))

    text = []

    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            text.append(paragraph.text)

    for table in document.tables:
        for row in table.rows:
            cells = [
                cell.text.strip()
                for cell in row.cells
            ]

            text.append(" | ".join(cells))

    return "\n".join(text)


def read_pdf_file(file):
    content = download_canvas_file(file)

    reader = PdfReader(BytesIO(content))

    text = []

    for page in reader.pages:
        page_text = page.extract_text()

        if page_text:
            text.append(page_text)

    return "\n".join(text)


def read_course_file(file):
    filename = file.get(
        "display_name",
        ""
    ).lower()

    if filename.endswith(".docx"):
        return read_word_file(file)

    if filename.endswith(".pdf"):
        return read_pdf_file(file)

    return None

def get_linked_files(description_html):
    if not description_html:
        return []

    soup = BeautifulSoup(
        description_html,
        "html.parser"
    )

    files = []

    for link in soup.find_all("a"):

        return_type = link.get(
            "data-api-returntype"
        )

        api_endpoint = link.get(
            "data-api-endpoint"
        )

        if return_type != "File":
            continue

        if not api_endpoint:
            continue

        try:
            response = requests.get(
                api_endpoint,
                headers=HEADERS,
                timeout=10,
            )

            response.raise_for_status()

            files.append(
                response.json()
            )

        except requests.RequestException:
            continue

    return files


# Tools
def get_upcoming_assignments(course_id: str) -> str:
    """
    Get all Canvas assignments with a future due date for a specific course.
    """

    if not CANVAS_TOKEN:
        return json.dumps({
            "error": "CANVAS_TOKEN is not set."
        })

    now = datetime.now(timezone.utc)

    url = (
        f"{CANVAS_URL}/api/v1/courses/"
        f"{course_id}/assignments"
    )

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            params={
                "per_page": 100,
                "include[]": "all_dates",
                "override_assignment_dates": True,
            },
            timeout=10,
        )

        response.raise_for_status()
        assignments = response.json()

    except requests.RequestException as e:
        return json.dumps({
            "error": f"Canvas assignment request failed: {e}"
        })

    results = []

    for assignment in assignments:
        due_at = assignment.get("due_at")

        if not due_at:
            continue

        try:
            due_time = datetime.fromisoformat(
                due_at.replace("Z", "+00:00")
            )
        except ValueError:
            continue

        # Skip assignments whose due date has already passed
        if due_time < now:
            continue

        description_html = assignment.get("description", "")
        description_text = clean_html(description_html)

        attachments = []

        linked_files = get_linked_files(description_html)

        for file in linked_files:
            filename = file.get("display_name", "")

            try:
                file_text = read_course_file(file)

                if file_text:
                    attachments.append({
                        "filename": filename,
                        "content": file_text,
                    })

            except Exception as e:
                attachments.append({
                    "filename": filename,
                    "error": f"Could not read file: {e}",
                })

        results.append({
            "assignment_id": assignment.get("id"),
            "name": assignment.get("name"),
            "due_at": assignment.get("due_at"),
            "points_possible": assignment.get("points_possible"),
            "submission_types": assignment.get("submission_types"),
            "instructions": description_text,
            "attached_files": attachments,
        })

    return json.dumps({
        "course_id": course_id,
        "assignment_count": len(results),
        "assignments": results,
    })

def get_course_file(
    course_id: str,
    filename: str
) -> str:
    """
    Find and read a PDF or Word file from a Canvas course.

    Use this when assignment instructions refer to a file by name,
    but that file was not already returned by get_upcoming_assignments.
    """

    if not CANVAS_TOKEN:
        return json.dumps({
            "error": "CANVAS_TOKEN is not set."
        })

    url = (
        f"{CANVAS_URL}/api/v1/courses/"
        f"{course_id}/files"
    )

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            params={
                "search_term": filename,
                "per_page": 100,
            },
            timeout=10,
        )

        response.raise_for_status()

        files = response.json()

    except requests.RequestException as e:
        return json.dumps({
            "error": (
                f"Canvas file search failed: {e}"
            )
        })

    if not files:
        return json.dumps({
            "error": (
                f"File '{filename}' was not found "
                f"in course {course_id}."
            )
        })

    filename_lower = filename.lower()

    selected_file = None

    # Prefer exact filename match
    for file in files:
        display_name = file.get(
            "display_name",
            ""
        ).lower()

        if display_name == filename_lower:
            selected_file = file
            break

    # Otherwise use the first partial match
    if selected_file is None:
        selected_file = files[0]

    actual_filename = selected_file.get(
        "display_name",
        ""
    )

    try:
        file_text = read_course_file(
            selected_file
        )

    except Exception as e:
        return json.dumps({
            "error": (
                f"Could not read "
                f"'{actual_filename}': {e}"
            )
        })

    if file_text is None:
        return json.dumps({
            "error": (
                f"'{actual_filename}' is not "
                "a supported PDF or Word file."
            )
        })

    return json.dumps({
        "course_id": course_id,
        "filename": actual_filename,
        "content": file_text,
    })

def get_courses() -> str:
    """
    Get the user's active Canvas courses.

    Returns the course ID, course name, and course code for each active course.

    Use this when the user refers to a course by name but the Canvas course ID
    is not already known. The returned course ID can then be used with other
    Canvas tools such as get_upcoming_assignments or get_course_file.
    """
    
    url = f"{CANVAS_URL}/api/v1/courses"

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            params={
                "enrollment_state": "active",
                "per_page": 100,
            },
            timeout=10,
        )

        response.raise_for_status()
        courses = response.json()

    except requests.RequestException as e:
        return json.dumps({
            "error": f"Canvas course request failed: {e}"
        })

    results = []

    for course in courses:
        results.append({
            "course_id": course.get("id"),
            "name": course.get("name"),
            "course_code": course.get("course_code"),
        })

    return json.dumps({
        "courses": results
    })

# What the model sees: the "set notes" in the screenplay.
TOOLS = [
   {
    "type": "function",
    "function": {
        "name": "get_upcoming_assignments",
        "description": (
            "Get assignments that are due soon for a specific Canvas course. "
            "Returns the Canvas assignment instructions and reads directly attached "
            "PDF or Word files when available. Use this first when the user asks "
            "about upcoming homework, workload, deadlines, or how long assignments may take."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "course_id": {
                    "type": "string",
                    "description": "The Canvas course ID."
                },
                "days": {
                    "type": "integer",
                    "description": (
                        "Number of upcoming days to check. "
                        "Use 14 if the user does not specify a time period."
                    ),
                    "minimum": 1
                }
            },
            "required": ["course_id"]
            }
        }
    },
    {
    "type": "function",
    "function": {
        "name": "get_course_file",
        "description": (
            "Find and read a specific file from a Canvas course. "
            "Use this when assignment instructions refer to a PDF or Word file "
            "whose contents were not already returned by get_upcoming_assignments. "
            "The tool searches for the file by name, downloads it, and returns its text."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "course_id": {
                    "type": "string",
                    "description": "The Canvas course ID."
                },
                "filename": {
                    "type": "string",
                    "description": (
                        "The file name mentioned in the assignment instructions, "
                        "such as 'HW3.pdf' or 'Project Instructions.docx'."
                    )
                }
            },
            "required": [
                "course_id",
                "filename"
            ]
            }
        }
    },
    {
    "type": "function",
    "function": {
        "name": "get_courses",
        "description": (
            "Get the user's active Canvas courses and their course IDs. "
            "Use this when a user refers to a course by name and the Canvas course ID "
            "is not already known."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            },
        },
    },
]

# What the harness runs: tool name -> Python function.
TOOL_MAP = {"get_upcoming_assignments": get_upcoming_assignments, "get_course_file": get_course_file, "get_courses": get_courses}


def run_tool(name: str, args: dict) -> str:
    """Run one tool call. Models invent tool names and arguments; never let that crash the loop."""
    if name not in TOOL_MAP:
        return json.dumps({"error": f"Unknown tool '{name}'. Available: {list(TOOL_MAP)}"})
    try:
        return TOOL_MAP[name](**args)
    except TypeError as e:
        return json.dumps({"error": f"Bad arguments for {name}: {e}"})
