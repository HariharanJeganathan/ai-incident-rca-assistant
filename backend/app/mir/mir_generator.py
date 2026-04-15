import base64
import json
import os

from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage


QUESTIONS_PROMPT = """You are an expert Major Incident Manager preparing questions for a Major Incident Review (MIR) meeting.

Based on the incident below, generate exactly 10 questions following these strict rules:

Q1-Q5: 5 Whys (Technical, Progressive, Non-Repetitive)
- Q1 must summarize what failed and where, written as a "Why" question
- Each Why must drill deeper technically into the root cause chain
- No repetition. No solutions. No answers. Only questions.

Q6: Immediate Corrective Action Question
- Ask what specific action was taken to restore service.

Q7: Preventive Action Question
- Ask what permanent control or validation should be implemented to prevent recurrence.

Q8-Q10: Gap Identification Questions
- Q8: Focus on monitoring or alerting gaps
- Q9: Focus on escalation or engagement delays
- Q10: Focus on testing, validation, change, or record lifecycle gaps
- Questions must be open-ended, not duplicate Q1-Q5, and target process weaknesses

Incident Title: {title}
Description: {description}
Resolution: {resolution}
Business Impact: {business_impact}

Return ONLY a valid JSON array of exactly 10 strings, no markdown, no explanation:
["Q1 text", "Q2 text", "Q3 text", "Q4 text", "Q5 text", "Q6 text", "Q7 text", "Q8 text", "Q9 text", "Q10 text"]
"""

HEADING_PROMPT = """Generate a short, powerful impact heading for this incident.

Rules:
- Maximum 8-12 words
- Written in past tense
- Clearly state what failed and why
- No unnecessary filler words (avoid: "An issue occurred", "There was a problem")
- No assumptions beyond what is stated
- Example: "Pickup Scheduling Failed Due to Database Record Expiry"

Incident Description: {description}
Resolution: {resolution}

Return ONLY the heading text, nothing else. No quotes, no punctuation at the end."""

TIMELINE_REVIEW_PROMPT = """You are reviewing an incident timeline against Major Incident Review (MIR) standards.

Timeline image or data provided. Check each criterion and classify as PASS, FAIL, or MISSING.

MIR Timeline Criteria:
1. Incident Started - time is recorded
2. Alert Reported - time is recorded
3. First IT Group Notified - time is recorded
4. Required Group Engaged - time is recorded
5. Corrective Action Determined - time is recorded
6. System at Useable Level (Incident Ended) - time is recorded
7. Checkout Completed - time is recorded
8. ALERTING Comment - present, names the monitoring tool and receiving team
9. AWARENESS Comment - present, names the first technical team made aware
10. ESCALATION Comment - present or explicitly N/A
11. TRIAGE Comment - present with issue summary and troubleshooting overview
12. REMEDIATION Comment - present with specific resolution action taken
13. CHECKOUT Comment - present, names the team that confirmed resolution
14. Writing style - all sentences end with period ".", written in past tense, one-liners
15. No personal pronouns or personal names used in comments

Gaps: Flag any gap between consecutive timeline timestamps that exceeds 30 minutes as needing justification.

Return ONLY valid JSON in this exact format:
{
  "criteria": [
    {"id": 1, "name": "Incident Started", "status": "PASS", "note": "Time recorded: 09:30 CT"},
    {"id": 2, "name": "Alert Reported", "status": "FAIL", "note": "Time missing from timeline"}
  ],
  "gaps_over_30min": [
    {"between": "Alert Reported -> First IT Group Notified", "duration": "45 min", "action": "Add justification comment explaining the delay"}
  ],
  "overall": "NEEDS_REVIEW",
  "summary": "5 criteria passed, 3 need attention, 1 gap flagged over 30 minutes"
}"""

MEETING_EMAIL_PROMPT = """You are a Major Incident Manager preparing a meeting invitation email for a Major Incident Review (MIR).

Incident: {inc_number}
Problem: {prb_number}
Title: {title}
Impact Heading: {impact_heading}
Questions (will be discussed):
{questions}

Generate a professional email body for the MIR meeting invite.
- Formal but concise
- Reference the INC and PRB numbers
- Mention the purpose is to review root cause and agree on CAPA
- Include a brief note that the questions will be discussed
- Do not include actual answers
- End with a call to action to confirm attendance

Return ONLY the email body text, no subject line, no greetings, just the body paragraphs."""


class MIRGenerator:

    def __init__(self):
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        key = os.getenv("AZURE_OPENAI_API_KEY")
        version = os.getenv("AZURE_OPENAI_API_VERSION")
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

        if not endpoint or not key or not version or not deployment:
            raise ValueError("Azure OpenAI environment variables are missing.")

        self.llm = AzureChatOpenAI(
            azure_endpoint=endpoint,
            api_key=key,
            api_version=version,
            deployment_name=deployment,
            max_tokens=2000,
        )

    def generate_questions(self, title: str, description: str, resolution: str, business_impact: str) -> list[str]:
        prompt = QUESTIONS_PROMPT.format(
            title=title,
            description=description,
            resolution=resolution,
            business_impact=business_impact,
        )
        response = self.llm.invoke(prompt)
        content = response.content.strip()
        # Strip markdown code fences if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        questions = json.loads(content)
        return questions[:10]

    def generate_impact_heading(self, description: str, resolution: str) -> str:
        prompt = HEADING_PROMPT.format(description=description, resolution=resolution)
        response = self.llm.invoke(prompt)
        return response.content.strip().strip('"')

    def generate_meeting_email(
        self,
        inc_number: str,
        prb_number: str,
        title: str,
        impact_heading: str,
        questions: list[str],
    ) -> str:
        numbered = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))
        prompt = MEETING_EMAIL_PROMPT.format(
            inc_number=inc_number,
            prb_number=prb_number,
            title=title,
            impact_heading=impact_heading,
            questions=numbered,
        )
        response = self.llm.invoke(prompt)
        return response.content.strip()

    def review_timeline_image(self, image_bytes: bytes, mime_type: str = "image/png") -> dict:
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        message = HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": TIMELINE_REVIEW_PROMPT,
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{b64}"},
                },
            ]
        )
        response = self.llm.invoke([message])
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)
