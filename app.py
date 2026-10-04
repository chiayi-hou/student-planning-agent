import json
import uuid
from pathlib import Path

import litellm
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from tools import TOOLS, run_tool, test_canvas_token

# --- Config ---

SYSTEM_PROMPT = (
   "You are a student planning assistant that helps users understand their upcoming "
    "assignments, estimate how long they will take, and decide when to start working on them. "

    "Never assume that Canvas is connected. Do not claim that Canvas is connected based only "
    "on the availability of Canvas tools or previous conversation. If the user asks whether "
    "Canvas is connected, call get_courses to verify access for the current session. "
    "If the tool succeeds, you may say Canvas is connected. If it fails because Canvas is not "
    "connected or no token is available, tell the user to connect Canvas and confirm that the "
    "interface shows 'Canvas connected'. "
    
    "When the user asks about upcoming homework, assignments, workload, deadlines, or how "
    "long an assignment may take, call get_upcoming_assignments first. "
    "By default, only discuss assignments whose due dates have not yet passed. "
    "Read the assignment instructions and any attached file contents returned by the tool carefully. "

    "If the assignment instructions refer to a PDF or Word file whose contents were not "
    "already returned, call get_course_file using the course ID and the referenced filename. "
    "Do not call get_course_file if the necessary file content has already been provided. "

    "Before estimating workload, make sure you have read all available instructions that are "
    "necessary to understand the assignment. Base the estimate on the actual tasks required, "
    "such as reading, calculations, coding, writing, debugging, data analysis, or creating "
    "figures. Break the assignment into major parts when useful and estimate how much time "
    "each part may take. "

    "Clearly distinguish between information stated in the assignment and your own estimated "
    "workload. Do not invent assignment requirements that are not present in the retrieved "
    "instructions or files. If the instructions are incomplete or a required file cannot be "
    "found, say that the estimate is uncertain and explain what information is missing. "

    "If the user refers to a course by name but its Canvas course ID is not known, "
    "call get_courses first and match the course name to the returned course before "
    "calling course-specific tools. "

    "When useful, recommend when the user should start based on the estimated workload and "
    "due date. Do not invent the user's availability, class schedule, office hours, or other "
    "time commitments unless the user has explicitly provided them. Keep the response practical "
    "and easy to follow. "

    "When discussing assignments or workload without creating a chronological study schedule, "
    "organize the response by course. Start each course section with a Markdown level-2 heading "
    "in exactly this format: '## COURSE: Course Name'. Put all information related to that course "
    "under that heading until the next course section."
    "Always use the exact course name returned by Canvas in every '## COURSE:' heading. "
    "Do not shorten, abbreviate, rename, or paraphrase course names. Use the exact same course "
    "name consistently in normal responses and in study schedules so the interface can assign "
    "the same color to the same course. "
    "Use this format even when only one course is being discussed. "

   "When creating or updating a study schedule, organize the entire schedule in chronological "
    "order across all courses, from the earliest day and time to the latest. Do not group the "
    "schedule by course, and do not assume the user should finish one course before working on "
    "another. Interleave work from different courses when appropriate based on due dates, "
    "estimated workload, and progress needed. "

    "When you create or update a study schedule, you MUST place the complete schedule between "
    "the exact markers '[[SCHEDULE_START]]' and '[[SCHEDULE_END]]'. These markers are used by "
    "the interface to display the schedule separately from the conversation. Do not use these "
    "markers unless you are actually creating or updating a schedule. "

    "Always provide the complete current schedule inside the schedule markers, not only the "
    "parts that changed. A newly generated schedule replaces the previously displayed schedule. "

    "Inside the schedule, group study blocks by date. Start each date with a Markdown level-1 "
    "heading in exactly this style: '# Monday, October 5'. Under each date heading, each study "
    "block that belongs to a course must start with a Markdown level-2 heading in exactly this "
    "format: '## COURSE: Course Name'. On the next line, write the time range in bold, such as "
    "'**2:00 PM – 4:00 PM**'. On the following line, write the specific task to work on. "
    "Keep the dates and all study blocks in chronological order. "

    "Outside the schedule markers, briefly explain the plan or any important reasoning to the "
    "user. Do not repeat the full schedule outside the markers. "
    )
MAX_TOOL_ROUNDS = 5

# --- The Harness ---


def run_agent(
    messages: list[dict],
    canvas_token: str | None = None,
) -> tuple[str, list[dict]]:
    """Complete until the model answers without asking for a tool.

    Returns the final text and a record of every tool call made along the way.
    """
    tool_calls = []

    for _ in range(MAX_TOOL_ROUNDS):
        reply = litellm.completion(
            model="vertex_ai/gemini-3.5-flash-lite",
            vertex_location="global",
            messages=messages,
            tools=TOOLS,
        ).choices[0].message

        # Append assistant's reply (text, tool calls, or both) to the context.
        # model_dump() keeps it a plain dict: the raw object carries provider-specific
        # fields that trip Pydantic when LiteLLM re-serializes it next round.
        messages += [reply.model_dump()]

        if not reply.tool_calls:
            return reply.content, tool_calls

        # The harness, not the model, runs each tool and appends the result
        for call in reply.tool_calls:
            args = json.loads(call.function.arguments)
            result = run_tool(call.function.name, args, canvas_token=canvas_token,)
            tool_calls += [{"name": call.function.name, "args": args, "result": result}]

            messages += [{"role": "tool", "tool_call_id": call.id, "content": result}]

    return "Sorry, I hit my tool-call limit before finishing.", tool_calls


# --- Session Store ---

# session_id -> list of messages. In-memory, single process.
sessions: dict[str, list] = {}

# session_id -> Canvas access token
canvas_tokens: dict[str, str] = {}

# --- FastAPI App ---

app = FastAPI()


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None

class CanvasTokenRequest(BaseModel):
    session_id: str
    token: str

class ChatResponse(BaseModel):
    response: str
    session_id: str
    tool_calls: list[dict]


@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "index.html")

@app.post("/canvas-token")
def set_canvas_token(request: CanvasTokenRequest):
    token = request.token.strip()

    if not token:
        raise HTTPException(
            status_code=400,
            detail="Canvas token is empty.",
        )

    if not test_canvas_token(token):
        raise HTTPException(
            status_code=401,
            detail="Canvas token is invalid.",
        )

    canvas_tokens[request.session_id] = token

    return {
        "status": "connected",
    }

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    # Get or create the session
    session_id = request.session_id or str(uuid.uuid4())
    if session_id not in sessions:
        sessions[session_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Append user's message to the context
    sessions[session_id] += [{"role": "user", "content": request.message}]

    try:
        response, tool_calls = run_agent(sessions[session_id], canvas_token=canvas_tokens.get(session_id))
    except Exception as e:
        # Auth, billing, a model that is not running: show it in the chat, not as a 500.
        response, tool_calls = f"Model call failed: {type(e).__name__}: {str(e)[:300]}", []

    return ChatResponse(response=response, session_id=session_id, tool_calls=tool_calls)


@app.post("/clear")
def clear(session_id: str | None = None):
    sessions.pop(session_id, None)
    canvas_tokens.pop(session_id, None)
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
