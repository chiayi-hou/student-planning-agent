# Student Planning Agent

A web-based student planning assistant powered by Gemini and Columbia CourseWorks (Canvas).

The agent is designed for Columbia students who want help understanding upcoming assignments,
estimating workload, and planning when to work on different courses.

- The harness loop is based on `qwen-tool-calling`, wrapped in `run_agent()`.
- The session store and `/chat` endpoint are based on `qwen-web-chat`.
- The model is `vertex_ai/gemini-3.5-flash-lite` in the `global` location.
- The agent connects to Columbia CourseWorks to retrieve active courses, upcoming assignments,
  assignment instructions, and linked PDF or Word files.
- The agent estimates assignment workload and generates a chronological study schedule
  across multiple courses.
- Users can continue refining the generated schedule by providing additional availability,
  preferences, or course-specific constraints.
- Once the user is satisfied with the plan, the agent can post the study blocks to the user's
  Canvas Calendar.
- Tool calls made by the harness are displayed in the chat interface.
- Generated study schedules are displayed separately in the Study Plan panel and remain
  visible until the agent creates an updated schedule.

## Tools

- `get_courses` — Gets the user's active Canvas courses and course IDs.
- `get_upcoming_assignments` — Retrieves future assignments, assignment instructions, and
  directly linked PDF or Word files for a course.
- `get_course_file` — Finds and reads a specific PDF or Word file referenced by an assignment.
- `add_study_plan_to_canvas_calendar` — Posts the user's approved study plan to their personal
  Canvas Calendar.

## Running the Application on Your Own Device

If you would like to run the application locally instead of using the deployed version:

1. Use a GCP project with billing and the Agent Platform API enabled.
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

## How to Use

1. Open the deployed website or run the application locally.

2. Connect your Columbia CourseWorks account using a Canvas access token.

   See the next section, **Connecting Columbia CourseWorks**, for instructions on how to
   obtain a Canvas access token.

3. Ask the assistant about upcoming assignments, workload, deadlines, or study planning.

4. Review the generated Study Plan on the left side of the interface.

5. Continue refining the plan by telling the assistant about your preferences or constraints.

6. Once the plan looks good, ask the assistant to post the study plan to your Canvas Calendar.

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

8. Return to the Student Planning Agent.

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

## Main Features

### 1. Assignment Understanding

The agent retrieves upcoming assignments from Columbia CourseWorks, reads available
instructions and linked files, and estimates how much time each assignment may take.

It can also compare workload across courses and help the user decide which assignments
should be started first.

### 2. Study Plan Creation and Refinement

The agent creates a chronological study plan across multiple courses based on assignment
deadlines, estimated workload, and difficulty.

The user can then refine the plan conversationally by providing additional preferences or
constraints, such as preferred study times, busy days, or professor office hours. The updated
plan replaces the previous plan in the **Study Plan** panel.

### 3. Canvas Calendar Integration

Once the user is satisfied with the Study Plan, the agent can post the planned study blocks
to the user's personal Canvas Calendar.

Each study block is converted into a timed calendar event containing the course, task,
date, start time, end time, and task description. The agent only writes to Canvas after
the user explicitly asks it to do so.

## Example Queries

Try:

```text
Do I have any upcoming assignments for my [replace_your_course_name_here] class?
```

```text
What homework do I have for [replace_your_course_name_here]?
```

```text
How long do you think my [replace_your_course_name_here] homework will take?
```

```text
What assignments do I have coming up across my courses?
```

```text
Which assignment should I start first?
```

```text
Make me a study schedule for my upcoming assignments.
```

```text
Update the schedule so I work on [replace_your_course_name_here] earlier.
```

```text
Make Tuesday lighter and move some work to Wednesday.
```

```text
I wake up early on Friday, so schedule more work that morning.
```

```text
My professor has office hours on Wednesday.
Make sure I start the assignment before then.
```

```text
This looks good. Post the plan to my Canvas Calendar.
```

## Notes

This application is currently designed specifically for Columbia University's CourseWorks
system, which is based on Canvas. It has not been tested with other universities' Canvas
instances.

The assistant does not automatically know the user's personal class schedule, sleep schedule,
office hours, or other time commitments unless the user explicitly provides that information.

Users can provide these constraints conversationally, and the agent can use them when
updating the Study Plan.

The application stores conversation state and Canvas connection information by session
while the server is running.

Canvas Calendar events created by the agent are written only after explicit user approval.

For a production system, persistent user authentication and Canvas OAuth could be used
instead of session-based access-token entry.