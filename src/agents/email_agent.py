"""Email agent that reads Gmail messages (read-only, no sending)."""

from __future__ import annotations

import os.path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from src.agents.base_agent import BaseAgent

# Dozvola za citanje i slanje email-ova (slanje uvek uz potvrdu korisnika)
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


class EmailAgent(BaseAgent):
    """Agent that reads Gmail messages. Read-only for safety."""

    def __init__(self, name: str = "EmailAgent") -> None:
        super().__init__(name=name)
        self.creds = None

    def _authenticate(self):
        """Uloguje se na Gmail preko OAuth-a i sacuva token za sledeci put."""
        creds = None

        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "gmail_credentials.json", SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open("token.json", "w") as token:
                token.write(creds.to_json())

        return creds

    def run(self, task: Any) -> str:
        """Proveri nekoliko poslednjih nepročitanih email-ova."""
        try:
            creds = self._authenticate()
            service = build("gmail", "v1", credentials=creds)

            results = (
                service.users()
                .messages()
                .list(userId="me", labelIds=["UNREAD"], maxResults=5)
                .execute()
            )
            messages = results.get("messages", [])

            if not messages:
                return "Nemas nepročitanih email-ova."

            lines = []
            for msg in messages:
                msg_data = (
                    service.users()
                    .messages()
                    .get(userId="me", id=msg["id"], format="metadata",
                         metadataHeaders=["Subject", "From"])
                    .execute()
                )
                headers = msg_data.get("payload", {}).get("headers", [])
                subject = next((h["value"] for h in headers if h["name"] == "Subject"), "(bez naslova)")
                sender = next((h["value"] for h in headers if h["name"] == "From"), "(nepoznat posiljalac)")
                lines.append(f"Od: {sender}\nNaslov: {subject}\n")

            return "\n".join(lines)

        except Exception as exc:
            return f"Greska pri citanju email-a: {exc}"

    def send_email(self, to: str, subject: str, body: str) -> str:
        """Posalji email. Poziva se TEK nakon potvrde korisnika."""
        try:
            import base64
            from email.mime.text import MIMEText

            creds = self._authenticate()
            service = build("gmail", "v1", credentials=creds)

            message = MIMEText(body)
            message["to"] = to
            message["subject"] = subject
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

            service.users().messages().send(
                userId="me", body={"raw": raw}
            ).execute()

            return f"Email uspesno poslat na {to}."

        except Exception as exc:
            return f"Greska pri slanju email-a: {exc}"