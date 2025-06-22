# main.py
import hmac
import hashlib
from fastapi import FastAPI, Request, Header, HTTPException, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError, BaseModel
from typing import Optional

from core import config, database
from core.models import PREventPayload, IssueEventPayload, IssueCommentPayload, InstallationPayload
from core.handlers import handle_pull_request_event, handle_issue_event, handle_issue_comment_event, \
    handle_installation_event

app = FastAPI(title="PullRider AI Assistant", version="1.0.0")
templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
async def startup_event():
    await database.create_tables()


class DashboardStats(BaseModel):
    total_prs_opened: int
    total_issues_opened: int
    last_pr_title: Optional[str]
    last_issue_title: Optional[str]
    repo_health_status: str


async def verify_github_signature(request: Request, x_hub_signature_256: str = Header(None)):
    if not x_hub_signature_256:
        raise HTTPException(status_code=400, detail="X-Hub-Signature-256 header is missing!")
    payload_body = await request.body()
    hash_object = hmac.new(config.GITHUB_WEBHOOK_SECRET.encode('utf-8'), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + hash_object.hexdigest()
    if not hmac.compare_digest(expected_signature, x_hub_signature_256):
        raise HTTPException(status_code=403, detail="Request signature does not match!")


@app.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request, installation_id: int):
    return templates.TemplateResponse("setup.html", {"request": request, "installation_id": installation_id})


@app.post("/setup/save")
async def save_setup(installation_id: int = Form(...), gemini_api_key: str = Form(...)):
    await database.save_api_key(installation_id, gemini_api_key)
    return RedirectResponse(url="/setup/success", status_code=303)


@app.get("/setup/success", response_class=HTMLResponse)
async def success_page(request: Request):
    return templates.TemplateResponse("success.html", {"request": request})


@app.post("/api/github/webhook", dependencies=[Depends(verify_github_signature)])
async def github_webhook(request: Request, x_github_event: str = Header(None)):
    payload = await request.json()

    installation_id = payload.get("installation", {}).get("id")
    if not installation_id:
        print("❌ CRITICAL: No installation ID in webhook payload.")
        return {"status": "error_no_installation_id"}

    event_handlers = {
        "pull_request": (PREventPayload, handle_pull_request_event),
        "issues": (IssueEventPayload, handle_issue_event),
        "issue_comment": (IssueCommentPayload, handle_issue_comment_event),
        "installation": (InstallationPayload, handle_installation_event),
    }

    if x_github_event in event_handlers:
        model, handler = event_handlers[x_github_event]
        try:
            payload_model = model(**payload)

            # THE FIX IS HERE: We now check the event type before calling the handler.
            # The 'installation' handler is special and only needs one argument.
            if x_github_event == "installation":
                await handler(payload_model)
            else:
                await handler(payload_model, installation_id)

            return {"status": f"Event '{x_github_event}' processed."}
        except ValidationError as e:
            print(f"❌ CRITICAL: Pydantic validation error for {x_github_event}: {e}")
            return {"status": "validation_error"}

    return {"status": "Event received, no handler."}


@app.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_data():
    return await database.get_dashboard_stats()


@app.get("/")
async def read_root():
    return {"message": f"{config.BOT_NAME} is alive and listening! 🐎"}
