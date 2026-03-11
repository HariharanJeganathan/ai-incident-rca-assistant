import os
from langchain_core.prompts import PromptTemplate
from langchain_openai import AzureChatOpenAI


class RCAGenerator:

    def __init__(self):

        # Azure OpenAI LLM configuration
        self.llm = AzureChatOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            temperature=0.2
        )

        # RCA Prompt Template
        self.prompt = PromptTemplate(
            input_variables=["incident", "similar_incidents"],
            template="""
You are an expert Site Reliability Engineer.

Analyze the new incident and similar past incidents to generate
a professional Root Cause Analysis report.

New Incident:
{incident}

Similar Past Incidents:
{similar_incidents}

Generate structured RCA with the following sections:

Problem Summary
Root Cause
Contributing Factors
Immediate Fix
Corrective Actions
Preventive Actions
Impact Summary

Also classify the incident impact:

Impact Classification:
- Severity: Low / Medium / High / Critical
- Regions impacted
- Services impacted
- Estimated users affected
"""
        )

    def generate_rca(self, incident, similar_incidents):

        prompt_text = self.prompt.format(
            incident=incident,
            similar_incidents=similar_incidents
        )

        response = self.llm.invoke(prompt_text)

        return response.content