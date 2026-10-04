#CLIENT_ID = "828235103430-0ns6rk3qmkd9p3s3p70i00bpjpesljgq.apps.googleusercontent.com"

from flask import Flask, redirect, request, session
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

app = Flask(__name__)
app.secret_key = "temporary-testing-secret"

CLIENT_SECRETS_FILE = "client_secret.json"

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events.readonly"
]

REDIRECT_URI = "http://localhost:8080/oauth2callback"


@app.route("/")
def index():
    return """
    <h2>Google Calendar Test</h2>
    <a href="/authorize">Connect Google Calendar</a>
    """


@app.route("/authorize")
def authorize():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        autogenerate_code_verifier=False,
    )

    flow.redirect_uri = REDIRECT_URI

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )

    session["state"] = state

    return redirect(authorization_url)


@app.route("/oauth2callback")
def oauth2callback():
    state = session["state"]

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state,
        autogenerate_code_verifier=False,
    )

    flow.redirect_uri = REDIRECT_URI

    flow.fetch_token(
        authorization_response=request.url
    )

    credentials = flow.credentials

    session["credentials"] = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }

    return redirect("/events")


@app.route("/events")
def events():
    from google.oauth2.credentials import Credentials

    creds = Credentials(
        **session["credentials"]
    )

    service = build(
        "calendar",
        "v3",
        credentials=creds,
    )

    events_result = (
        service.events()
        .list(
            calendarId="primary",
            maxResults=10,
            singleEvents=True,
            orderBy="startTime",
            timeMin=__import__("datetime")
            .datetime.now(
                __import__("datetime").timezone.utc
            )
            .isoformat(),
        )
        .execute()
    )

    events = events_result.get("items", [])

    if not events:
        return "Connected successfully, but no upcoming events were found."

    output = "<h2>Upcoming Events</h2>"

    for event in events:
        start = event["start"].get(
            "dateTime",
            event["start"].get("date")
        )

        title = event.get(
            "summary",
            "(No title)"
        )

        output += f"<p>{start} — {title}</p>"

    return output


if __name__ == "__main__":
    app.run(
        host="localhost",
        port=8080,
        debug=True,
    )