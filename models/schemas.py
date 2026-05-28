from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
import uuid
from datetime import datetime

class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class IssueType(str, Enum):
    BUG = "BUG"
    SECURITY = "SECURITY"
    PERFORMANCE = "PERFORMANCE"

class Issue(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique UUID for this issue")
    file: str = Field(..., description="File path where the issue occurs")
    line: int = Field(..., description="Line number where the issue starts")
    type: IssueType = Field(..., description="Category of the issue")
    severity: Severity = Field(..., description="Impact level")
    description: str = Field(..., description="Clear explanation of the problem, root cause, and impact")

class Fix(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique UUID for this fix")
    issue_id: str = Field(..., description="Reference to the Issue ID")
    original_code: str = Field(..., description="The exact buggy section of code")
    proposed_code: str = Field(..., description="The refactored, corrected code")
    explanation: str = Field(..., description="Why this proposed fix solves the issue and its safety")

class FixEvaluation(BaseModel):
    fix_id: str = Field(..., description="Reference to the Fix ID")
    correctness_score: int = Field(..., ge=0, le=100, description="Score based on algorithmic correctness")
    security_score: int = Field(..., ge=0, le=100, description="Score based on vulnerability mitigation")
    compatibility_score: int = Field(..., ge=0, le=100, description="Score based on API backward compatibility")
    risk_level: Severity = Field(..., description="Risk of deploying this change (e.g., side effects)")
    confidence: int = Field(..., ge=0, le=100, description="Aggregated confidence percentage")
    confidence_score: Optional[int] = Field(None, ge=0, le=100, description="Alias for confidence score")
    reasoning: str = Field(..., description="Exhaustive logic explaining the assigned scores")

class ReviewSession(BaseModel):
    pr_id: str = Field(..., description="GitHub Pull Request identification number/string")
    repo_name: str = Field(..., description="Repository full name (org/repo)")
    commit_sha: str = Field(default="unknown", description="Head commit SHA for the PR branch")
    pr_title: str = Field(default="", description="Title of the PR")
    pr_body: str = Field(default="", description="Description/Body of the PR")
    status: str = Field(default="pending", description="Current status of the review session")
    issues: List[Issue] = Field(default_factory=list)
    fixes: List[Fix] = Field(default_factory=list)
    evaluations: Dict[str, FixEvaluation] = Field(default_factory=dict) # fix_id -> FixEvaluation
    human_decisions: Dict[str, str] = Field(default_factory=dict) # fix_id -> 'approved' | 'rejected' | 'pending'
    applied_fixes: List[str] = Field(default_factory=list) # List of fix_ids
    cost: float = Field(default=0.0, description="Total API and token cost logged for the session")
    tokens_used: int = Field(default=0, description="Total tokens consumed")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
