import os
from langchain_core.prompts import PromptTemplate
from langchain_openai import AzureChatOpenAI


class RCAGenerator:

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
            max_tokens=1200
        )

        self.prompt = PromptTemplate(
            input_variables=["incident", "similar_incidents"],
            template="""
You are a senior Site Reliability Engineer performing a Root Cause Analysis.

Analyze the incident data and similar past incidents.

New Incident:
{incident}

Similar Past Incidents:
{similar_incidents}

Generate a professional RCA report with the following sections:

1. Problem Summary
2. Root Cause
3. Contributing Factors
4. Immediate Fix
5. Corrective Actions
6. Preventive Actions
7. Impact Summary

Impact Classification:
- Severity Level: Low / Medium / High / Critical
- Regions Impacted
- Services Impacted
- Estimated Users Affected

Write clearly and professionally as if submitting to incident management leadership.
"""
        )

    def generate_rca(self, incident, similar_incidents):

        prompt_text = self.prompt.format(
            incident=incident,
            similar_incidents=similar_incidents
        )

        response = self.llm.invoke(prompt_text)

        return response.content