# student-planning-agent

A web-based student planning assistant powered by Gemini and Columbia CourseWorks (Canvas).

- The harness loop is based on `qwen-tool-calling`, wrapped in `run_agent()`.
- The session store and `/chat` endpoint are based on `qwen-web-chat`.
- The model is `vertex_ai/gemini-3.5-flash-lite` in the `global` location.
- The agent connects to Columbia CourseWorks to retrieve active courses, upcoming assignments,
  assignment instructions, and linked PDF or Word files.
- The agent estimates assignment workload and generates a chronological study schedule
  across multiple courses.
- Users can continue refining the generated schedule through conversation by providing
  additional availability, preferences, or course-specific constraints.
- Once the user is satisfied with the plan, the agent can post the study blocks to the user's
  Canvas Calendar.
- `/chat` also returns the tool calls made by the harness, and the page displays them
  above the assistant's response.
- Generated study schedules are displayed separately in the Study Plan panel and remain
  visible until the agent creates an updated schedule.

## Setup

1. A GCP project with billing and the Agent Platform API enabled.
   Older documentation and the endpoint itself may still refer to Vertex AI.

2. Authenticate with Google Cloud:

   ```bash
   gcloud auth application-default login
   ```

3. Run the application:

   ```bash
   uv run app.py
   ```

4. Open the application in your browser:

   ```text
   http://localhost:8000
   ```

## Connecting Columbia CourseWorks

The application requires a Canvas access token in order to access your own courses,
assignments, and Canvas Calendar.

To obtain a token from Columbia CourseWorks:

1. Open Columbia CourseWorks:

   ```text
   https://courseworks2.columbia.edu
   ```

2. Click **Account** in the left sidebar.

3. Open **Settings**.

4. Scroll to the **Approved Integrations** section.

5. Click **+ New Access Token**.

6. Enter a purpose for the token, for example:

   ```text
   Student Planning Agent
   ```

7. Generate the token and copy it.

8. Open the student planning application.

9. Paste the token into the **Canvas Access Token** field.

10. Click **Connect Canvas**.

11. Wait until the interface shows:

   ```text
   Canvas connected ✓
   ```

The Canvas token is used by the backend to access the Canvas account associated with
the current session.

The token is not:

- included in the model's tool-call arguments,
- displayed in the chat,
- stored in the GitHub repository.

Do not commit or publicly share your Canvas access token.

## How to Use the Website

After connecting Canvas, you can ask the assistant questions about your courses and assignments.

For example:

```text
Do I have any upcoming assignments for my computer vision class?
```

The agent can identify the correct course and retrieve its future assignments.

You can also ask:

```text
How long do you think my statistics homework will take?
```

The agent will inspect the assignment instructions and available attached files before
estimating the workload.

To check multiple courses, try:

```text
What assignments do I have coming up across my courses?
```

The assistant can retrieve assignment information from multiple Canvas courses and
organize the response by course.

## Study Planning

The assistant can create a chronological study schedule across multiple courses.

For example:

```text
Make me a study schedule for my upcoming assignments.
```

The schedule is ordered by day and time rather than grouping all work from one course together.

Work from different courses may be interleaved based on:

- assignment due dates,
- estimated workload,
- difficulty,
- progress needed before the deadline.

The generated schedule is displayed in the **Study Plan** panel on the left side of the interface.

The Study Plan remains visible while you continue chatting.

## Refining the Study Plan

The first generated plan does not have to be final.

After reviewing the plan, you can continue talking to the agent and provide additional
information about your availability, preferences, or course-specific constraints.

For example:

```text
I wake up earlier on Wednesday, so you can schedule some work earlier that morning.
```

```text
My statistics professor has office hours on Thursday afternoon.
I want to finish at least half of the homework before then so I know what questions to ask.
```

```text
Tuesday is too busy. Move some of the work to Wednesday.
```

```text
I want to start the computer vision assignment earlier because I think it will be difficult.
```

The agent uses the new information to generate an updated chronological plan.

When the schedule is updated, the new plan replaces the previous plan in the
**Study Plan** panel.

You can continue refining the plan until the schedule fits your actual availability
and preferences.

## Posting the Plan to Canvas Calendar

Once the Study Plan looks good, you can ask the agent to add it to your Canvas Calendar.

For example:

```text
This looks good. Post the study plan to my Canvas Calendar.
```

or:

```text
Add the schedule on the left to Canvas.
```

The agent converts each study block into a timed Canvas Calendar event using the planned:

- course and task,
- date,
- start time,
- end time,
- task description.

The agent only writes to Canvas when the user explicitly asks it to do so.

Creating or editing a study plan by itself does not automatically modify the user's
Canvas Calendar.

## Agent Tool Flow

Depending on the user's question, the agent may make multiple tool calls.

A typical workflow is:

1. Identify the correct Canvas course using `get_courses`.
2. Retrieve future assignments using `get_upcoming_assignments`.
3. Read the assignment description and directly linked PDF or Word files.
4. If the assignment refers to another course file that was not directly attached,
   retrieve it using `get_course_file`.
5. Estimate how much time the assignment may take.
6. Recommend when the user should begin working.
7. If requested, generate a chronological study schedule.
8. Allow the user to refine the schedule by providing additional constraints or preferences.
9. If the user explicitly approves the schedule and asks to save it, post the study blocks
   to Canvas using `add_study_plan_to_canvas_calendar`.

The agent is instructed not to invent assignment requirements that are not present in
the retrieved Canvas content.

## Available Tools

### `get_courses`

Returns the user's active Canvas courses and their Canvas course IDs.

This is used when the user refers to a course by name but the agent does not yet know
its Canvas course ID.

### `get_upcoming_assignments`

Returns assignments whose due dates have not yet passed for a specific Canvas course.

It includes:

- assignment name,
- due date,
- points possible,
- submission type,
- assignment instructions,
- directly linked PDF or Word file contents when available.

Due dates are interpreted using the `America/New_York` timezone.

### `get_course_file`

Searches for and reads a specific file from a Canvas course.

This is used when an assignment description references a PDF or Word file whose
contents were not already returned by `get_upcoming_assignments`.

### `add_study_plan_to_canvas_calendar`

Adds the user's approved study plan to their personal Canvas Calendar.

Each study block is converted into a timed calendar event containing:

- course and task title,
- start time,
- end time,
- task description.

This tool is only called after the user explicitly asks to add or post the current
study plan to Canvas.

## Example Prompts

Try:

```text
Do I have any upcoming assignments for my computer vision class?
```

```text
What homework do I have for statistics?
```

```text
How difficult does this assignment look?
```

```text
How long do you think this homework will take?
```

```text
What assignments do I have coming up across my courses?
```

```text
Make me a study schedule for my upcoming assignments.
```

```text
Update the schedule so I work on computer vision earlier.
```

```text
I wake up early on Friday, so schedule more work that morning.
```

```text
My professor has office hours on Wednesday.
Make sure I start the assignment before then.
```

```text
Make Tuesday lighter and move some work to Wednesday.
```

```text
Which assignment should I start first?
```

```text
This looks good. Post the plan to my Canvas Calendar.
```

## Notes

This application is currently designed specifically for Columbia University's
CourseWorks system, which is based on Canvas. It has not been tested with other
universities' Canvas instances.

The application uses Columbia CourseWorks data to understand course assignments
and deadlines.

The assistant does not automatically know the user's personal class schedule,
sleep schedule, office hours, or other time commitments unless the user explicitly
provides that information.

Users can provide these constraints conversationally, and the agent can use them
when updating the Study Plan.

The application stores conversation state and Canvas connection information by
session while the server is running.

Canvas Calendar events created by the agent are written only after explicit user approval.

For a production system, persistent user authentication and Canvas OAuth could be
used instead of session-based access-token entry.