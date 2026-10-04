# student-planning-agent

A web-based student planning assistant powered by Gemini and Canvas CourseWorks.

- The harness loop is based on `qwen-tool-calling`, wrapped in `run_agent()`.
- The session store and `/chat` endpoint are based on `qwen-web-chat`.
- The model is `vertex_ai/gemini-3.5-flash-lite` in the `global` location.
- The agent connects to Canvas CourseWorks to retrieve active courses, upcoming assignments,
  assignment instructions, and linked PDF or Word files.
- The agent estimates assignment workload and can generate a chronological study schedule
  across multiple courses.
- `/chat` also returns the tool calls made by the harness, and the page displays them
  above the assistant's response.
- Generated study schedules are displayed separately in the Study Plan panel and remain
  visible until the agent creates an updated schedule.

## Setup

1. A GCP project with billing and the Agent Platform API enabled
   (older documentation and the endpoint itself may still refer to Vertex AI).

2. Authenticate with Google Cloud:

   ```bash
   gcloud auth application-default login

3. Run the application:
   uv run app.py

4. Open the application in your browser:
   http://localhost:8000

## Connecting Canvas CourseWorks
The application requires a Canvas access token in order to read your own courses and assignments.
For Columbia CourseWorks:
1. Open Columbia CourseWorks:
   https://courseworks2.columbia.edu
2. Click **Account** in the left sidebar.

3. Open Settings.

4. Scroll to the Approved Integrations section.

5. Click **+ New Access Token**.

6. Enter a purpose for the token, for example:
   Student Planning Agent
7. Generate the token and copy it.
8. Open the student planning application.
9. Paste the token into the **Canvas Access Token** field.
10. Click **Connect Canvas**.
11. Wait until the interface shows:
   Canvas connected ✓

The Canvas token is used by the backend to access the Canvas account associated with the current session.
The token is not:
- included in the model's tool-call arguments,
- displayed in the chat,
- stored in the GitHub repository.
Do not commit or publicly share your Canvas access token.

## How to Use the Website
After connecting Canvas, you can ask the assistant questions about your courses and assignments.
For example:
"Do I have any upcoming assignments for my computer vision class?"
The agent can identify the course and retrieve its future assignments.

You can also ask:
"How long do you think my statistics homework will take?"
The agent will inspect the assignment instructions and available attached files before estimating the workload.

To check multiple courses, try:
"What assignments do I have coming up across my courses?"
The assistant can retrieve assignment information from multiple Canvas courses and organize the response by course.

## Study Planning
The assistant can also create a chronological study schedule across multiple courses.
For example:
"Make me a study schedule for my upcoming assignments."

The schedule is ordered by day and time rather than grouping all work from one course together.
Work from different courses may be interleaved based on:
- assignment due dates,
- estimated workload,
- difficulty,
- progress needed before the deadline.
The generated schedule is displayed in the Study Plan panel on the left side of the interface.

The Study Plan remains visible while you continue chatting.
If the assistant later generates an updated schedule, the new schedule replaces the previous one.
For example:
"Update the schedule so I start the harder assignment earlier."
or 
"Make Tuesday lighter and move some work to Wednesday."

## Agent Tool Flow
Depending on the user's question, the agent may make multiple tool calls.
A typical workflow is:
1. Identify the correct Canvas course using get_courses.
2. Retrieve future assignments using get_upcoming_assignments.
3. Read the assignment description and directly linked PDF or Word files.
4. If the assignment refers to another course file that was not directly attached,
   retrieve it using get_course_file.
5. Estimate how much time the assignment may take.
6. Recommend when the user should begin working.
7. If requested, generate a chronological study schedule.
The agent is instructed not to invent assignment requirements that are not present in the retrieved Canvas content.

## Available Tools
`get_courses`:
Returns the user's active Canvas courses and their Canvas course IDs.
This is used when the user refers to a course by name but the agent does not yet know its Canvas course ID.
`get_upcoming_assignments`:
Returns assignments whose due dates have not yet passed for a specific Canvas course. It includes:
- assignment name,
- due date,
- points possible,
- submission type,
- assignment instructions,
- directly linked PDF or Word file contents when available.
Due dates are interpreted using the America/New_York timezone.
`get_course_file`:
Searches for and reads a specific file from a Canvas course.
This is used when an assignment description references a PDF or Word file whose contents were not already returned by get_upcoming_assignments.

## Example Prompts
Try:
"Do I have any upcoming assignments for my computer vision class?"
"What homework do I have for statistics?"
"How difficult does this assignment look?"
"How long do you think this homework will take?"
"What assignments do I have coming up across my courses?"
"Make me a study schedule for my upcoming assignments."
"Update the schedule so I work on computer vision earlier."
"Which assignment should I start first?"

## Notes
The application currently focuses on Canvas CourseWorks data and does not automatically know the user's personal calendar, class schedule, office hours, or other time commitments unless the user explicitly provides that information.
The application stores conversation state and Canvas connection information by session while the server is running.
For a production system, persistent user authentication and Canvas OAuth could be used instead of session-based access-token entry.