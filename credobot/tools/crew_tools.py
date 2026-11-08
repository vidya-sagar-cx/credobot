"""CrewAI BaseTool wrappers for RAG and Loan Status lookup."""
import json
from pydantic import BaseModel, Field
from credobot import config  # noqa: F401
from credobot.tools.loan_status import check_loan_application_status
from credobot.tools.rag_tool import rag_lookup
from crewai.tools import BaseTool


class RagLookupInput(BaseModel):
    query: str = Field(..., description="The user's policy question")


class LoanStatusInput(BaseModel):
    record_id: str = Field(..., description="Loan application id like LA-1001")


class RagLookupTool(BaseTool):
    name: str = "rag_lookup"
    description: str = "Search the X Corp policy knowledge base and return a grounded answer."
    args_schema: type[BaseModel] = RagLookupInput

    def _run(self, query: str) -> str:
        return rag_lookup(query)


class LoanStatusTool(BaseTool):
    name: str = "check_loan_application_status"
    description: str = "Look up a loan application's status, amount and escalation score."
    args_schema: type[BaseModel] = LoanStatusInput

    def _run(self, record_id: str) -> str:
        return json.dumps(check_loan_application_status(record_id))
