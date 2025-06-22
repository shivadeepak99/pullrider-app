# core/models.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict

class GitHubUser(BaseModel):
    login: str

class Comment(BaseModel):
    body: str
    user: GitHubUser

class Issue(BaseModel):
    number: int
    title: str
    body: Optional[str] = ""
    user: GitHubUser
    comments_url: str
    pull_request: Optional[dict] = None

class PullRequest(BaseModel):
    number: int
    title: str
    body: Optional[str] = ""
    user: GitHubUser
    comments_url: str
    diff_url: str
    draft: bool

class Repository(BaseModel):
    full_name: str
    owner: GitHubUser

class PREventPayload(BaseModel):
    action: str
    pull_request: PullRequest = Field(..., alias='pull_request')
    repository: Repository

class IssueEventPayload(BaseModel):
    action: str
    issue: Issue
    repository: Repository

class IssueCommentPayload(BaseModel):
    action: str
    issue: Issue
    comment: Comment
    repository: Repository

# NEW: Model for when a user installs our App
class InstallationInfo(BaseModel):
    id: int
    account: GitHubUser

class InstallationPayload(BaseModel):
    action: str
    installation: InstallationInfo
    repositories: Optional[List[Dict]] = None
