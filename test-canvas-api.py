"""
Canvas API
"""
import requests
from io import BytesIO
from docx import Document
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
from pypdf import PdfReader


CANVAS_URL = "https://courseworks2.columbia.edu"
CANVAS_TOKEN = "1396~vvT99B87vKyPE6yxtDzU8EBhkkJhVmhNr2QHCJEaLG7QE9fE8tW9rXKCLR9r3RCk"


if not CANVAS_TOKEN:
    raise ValueError(
        "CANVAS_TOKEN is not set. "
        "Run: export CANVAS_TOKEN='your_token_here'"
    )


HEADERS = {
    "Authorization": f"Bearer {CANVAS_TOKEN}"
}


def get_courses():
    url = f"{CANVAS_URL}/api/v1/courses"

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

    return response.json()


def get_announcements(course_id, days=14):
    url = f"{CANVAS_URL}/api/v1/announcements"

    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)

    response = requests.get(
        url,
        headers=HEADERS,
        params={
            "context_codes[]": f"course_{course_id}",
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": now.strftime("%Y-%m-%d"),
            "per_page": 100,
        },
        timeout=10,
    )

    response.raise_for_status()
    return response.json()

def get_upcoming_assignments(course_id, days=14):
    url = f"{CANVAS_URL}/api/v1/courses/{course_id}/assignments"

    response = requests.get(
        url,
        headers=HEADERS,
        params={
            "bucket": "upcoming",
            "per_page": 100,
        },
        timeout=10,
    )

    response.raise_for_status()

    assignments = response.json()

    now = datetime.now(timezone.utc)
    end_time = now + timedelta(days=days)

    upcoming = []

    for assignment in assignments:
        due_at = assignment.get("due_at")

        if not due_at:
            continue

        due_time = datetime.fromisoformat(
            due_at.replace("Z", "+00:00")
        )

        if now <= due_time <= end_time:
            upcoming.append(assignment)

    return upcoming

def get_course_files(course_id):
    url = f"{CANVAS_URL}/api/v1/courses/{course_id}/files"

    response = requests.get(
        url,
        headers=HEADERS,
        params={
            "per_page": 100,
        },
        timeout=10,
    )

    response.raise_for_status()

    return response.json()


def read_word_file(file):
    file_url = file["url"]

    response = requests.get(
        file_url,
        headers=HEADERS,
        timeout=20,
    )

    response.raise_for_status()

    document = Document(BytesIO(response.content))

    text = []

    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            text.append(paragraph.text)

    # Also read tables, since homework instructions may use tables
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            text.append(" | ".join(cells))

    return "\n".join(text)


def clean_html(html):
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text("\n", strip=True)


# --------------------------------------------------
# 1. Show active courses
# --------------------------------------------------

print("\nACTIVE COURSES")
print("=" * 80)

courses = get_courses()

for course in courses:
    print(
        f"{course.get('id')} | "
        f"{course.get('name', 'Unnamed course')}"
    )


# --------------------------------------------------
# 2. Choose a course
# --------------------------------------------------

course_id = input(
    "\nEnter the course ID you want to test: "
).strip()


# --------------------------------------------------
# 3. Get announcements
# --------------------------------------------------

print("\nANNOUNCEMENTS")
print("=" * 80)

announcements = get_announcements(course_id)

if not announcements:
    print("No announcements found.")

else:
    for announcement in announcements:
        print("Title:", announcement.get("title"))
        print("Posted:", announcement.get("posted_at"))

        message = clean_html(
            announcement.get("message")
        )

        print("Message:")
        print(message)

        print("-" * 80)


# --------------------------------------------------
# 4. Get Word files
# --------------------------------------------------

print("\nWORD FILES")
print("=" * 80)

files = get_course_files(course_id)

word_files = [
    file
    for file in files
    if file.get("display_name", "")
    .lower()
    .endswith(".docx")
]

if not word_files:
    print("No .docx files found in this course.")
    raise SystemExit


for i, file in enumerate(word_files):
    print(
        f"{i}: {file.get('display_name')} "
        f"(file id: {file.get('id')})"
    )


# --------------------------------------------------
# 5. Choose and read one Word file
# --------------------------------------------------

file_index = int(
    input("\nEnter the number of the Word file to read: ")
)

selected_file = word_files[file_index]

print("\nREADING FILE")
print("=" * 80)

print("File:", selected_file["display_name"])
print()

word_text = read_word_file(selected_file)

print(word_text)