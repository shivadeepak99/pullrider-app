# core/handlers.py
import asyncio
import random
from typing import Optional
from .clients import GitHubClient, GeminiClient
from .models import PREventPayload, IssueEventPayload, IssueCommentPayload, PullRequest, Repository, InstallationPayload
from .config import BOT_NAME, GITHUB_TOKEN, GEMINI_API_KEY_FALLBACK
from .database import log_pr_event, log_issue_event, get_api_key_from_db


async def get_gemini_client_for_install(repo_full_name: str, installation_id: int) -> Optional[GeminiClient]:
    """Finds the correct API key for an installation and returns a Gemini client."""
    print(f"🔐 Finding API Key for repo '{repo_full_name}' (installation {installation_id})...")

    # This is a placeholder for a real implementation that would securely fetch secrets.
    # For now, we prioritize the DB key and then the fallback.
    github_client = GitHubClient(token=GITHUB_TOKEN)
    repo_secret = await github_client.get_repo_secret(repo_full_name, "PULLRIDER_GEMINI_KEY")
    if repo_secret:
        print("...Found key in repo secrets (Manual Setup).")
        return GeminiClient(api_key=repo_secret)

    db_key = await get_api_key_from_db(installation_id)
    if db_key:
        print("...Found key in database (Easy Setup).")
        return GeminiClient(api_key=db_key)

    if GEMINI_API_KEY_FALLBACK:
        print("...Using owner's fallback API key for local testing.")
        return GeminiClient(api_key=GEMINI_API_KEY_FALLBACK)

    print("...No API key found for this installation.")
    return None


async def handle_installation_event(payload: InstallationPayload):
    """Handles the event when a user first installs the app."""
    if payload.action == "created":
        install_id = payload.installation.id
        user = payload.installation.account.login
        print(f"🎉 New installation by '{user}' (ID: {install_id}). They should be redirected to setup.")


async def handle_pull_request_event(payload: PREventPayload, installation_id: int, force_review: bool = False,
                                    previous_review: Optional[str] = None):
    pr = payload.pull_request
    repo = payload.repository
    github_client = GitHubClient(token=GITHUB_TOKEN)
    print(f"\n--- Handling PR #{pr.number} in {repo.full_name} ---")

    # On any PR event, log it if it's new
    if payload.action == "opened":
        await log_pr_event(pr.number, repo.full_name, pr.title, pr.user.login)

    # Do not comment if the bot has already commented, unless forced
    if not force_review and await github_client.get_bot_last_comment(pr.comments_url):
        return

    # Check for Gemini client now, so we can post a setup message if needed
    gemini_client = await get_gemini_client_for_install(repo.full_name, installation_id)
    if not gemini_client:
        comment_body = ("👋 Hello! To get AI-powered reviews, please complete the setup. "
                        "You can re-install the app on this repo to access the setup page.")
        await github_client.post_comment(pr.comments_url, comment_body)
        print("🔑 User needs to complete setup. Posted instructions.")
        return

    # If this is a follow-up review, handle it differently
    if force_review and previous_review:
        print("🧠 Performing follow-up AI analysis...")
        diff_content = await github_client.get_pr_diff(pr.diff_url)
        if not diff_content: return
        ai_review = await gemini_client.follow_up_review(pr.title, diff_content, previous_review)
        comment_body = f"### 🤖 PullRider Follow-up\n\nHey @{pr.user.login}!\n\n{ai_review}"
        await github_client.post_comment(pr.comments_url, comment_body)
        print("--- Follow-up Review Complete ---")
        return

    # Standard initial review process
    if pr.draft:
        print("✍️ Detected Draft PR. Posting a friendly wait message.")
        comment_body = f"Hey @{pr.user.login}, thanks for starting this PR! I see it's still a draft, so I'll wait until you mark it as 'Ready for Review' before I do a full analysis. No pressure, just let me know when you're ready!"
        await github_client.post_comment(pr.comments_url, comment_body)
        return

    changed_files_data = await github_client.get_pr_files(repo.full_name, pr.number)
    if not changed_files_data: return

    filenames = [file['filename'] for file in changed_files_data]
    if all(f.endswith(('.md', '.txt')) or '.gitignore' in f for f in filenames):
        print("📄 Detected trivial change. Posting a simple thank you.")
        comment_body = f"Thanks for the cleanup, @{pr.user.login}! Appreciate you keeping the docs and project files tidy. I'll let the owner handle this quick merge."
        await github_client.post_comment(pr.comments_url, comment_body)
        return

    print("👁️ Awakening the Third Eye: Gathering full repo context...")
    custom_config = await github_client.get_config_file(repo.full_name)
    custom_rules = custom_config.get('rules', []) if custom_config else []

    diff_content = await github_client.get_pr_diff(pr.diff_url)
    if not diff_content: return

    file_contexts = {}
    tasks = [github_client.get_file_content(file['contents_url']) for file in changed_files_data if
             file['status'] != 'removed']
    fetched_contents = await asyncio.gather(*tasks)
    valid_files_data = [file for file in changed_files_data if file['status'] != 'removed']
    for i, file_info in enumerate(valid_files_data):
        if fetched_contents[i]:
            file_contexts[file_info['filename']] = fetched_contents[i]

    print(f"🧠 Performing context-aware AI analysis with {len(custom_rules)} custom rule(s)...")
    ai_review = await gemini_client.analyze_code_with_context(pr.title, diff_content, file_contexts, custom_rules)
    if "Error:" in ai_review: return

    comment_body = f"### 🤖 PullRider AI Review\n\nHey @{pr.user.login}!\n\n{ai_review}"
    await github_client.post_comment(url=pr.comments_url, body=comment_body)
    print("--- PR Processing Complete ---")


async def handle_issue_event(payload: IssueEventPayload, installation_id: int):
    issue = payload.issue
    repo = payload.repository
    github_client = GitHubClient(token=GITHUB_TOKEN)
    print(f"\n--- Handling Issue #{issue.number} for action '{payload.action}' ---")

    if payload.action != "opened":
        print(f"⏩ Ignoring issue action '{payload.action}'.")
        return

    await log_issue_event(issue.number, repo.full_name, issue.title, issue.user.login)

    if await github_client.get_bot_last_comment(issue.comments_url): return

    gemini_client = await get_gemini_client_for_install(repo.full_name, installation_id)
    if not gemini_client:
        print(f"🔑 No API key for installation {installation_id}, skipping AI issue analysis.")
        return

    category = await gemini_client.classify_issue(issue.title, issue.body)
    if category in ["Bug Report", "Feature Request", "Spam/Unclear"]:
        analysis = await gemini_client.get_issue_quality_analysis(issue.title, issue.body)
        comment_body = f"### 🤖 PullRider Issue Helper\n\nHello @{issue.user.login}! Thanks for opening this issue. Here's a quick analysis to help us get started:\n\n---\n\n{analysis}"
        await github_client.post_comment(url=issue.comments_url, body=comment_body)
    elif category == "Social":
        reply = await gemini_client.get_social_reply(issue.title, issue.user.login)
        await github_client.post_comment(url=issue.comments_url, body=reply)
        await github_client.close_issue(repo.full_name, issue.number)
    elif category == "Question":
        reply = f"Hey @{issue.user.login}! It looks like you have a question. For general questions, it's best to use the 'Discussions' tab... "
        await github_client.post_comment(url=issue.comments_url, body=reply)
        await github_client.close_issue(repo.full_name, issue.number)
    print("--- Issue Processing Complete ---")


async def handle_issue_comment_event(payload: IssueCommentPayload, installation_id: int):
    comment = payload.comment
    issue = payload.issue
    repo = payload.repository
    github_client = GitHubClient(token=GITHUB_TOKEN)

    is_summoned = f"@{BOT_NAME}" in comment.body
    is_on_pr = issue.pull_request is not None
    is_not_bot = comment.user.login != f"{BOT_NAME}[bot]"

    if is_on_pr and is_summoned and is_not_bot:
        print(f"--- Handling Summon on PR #{issue.number} ---")
        last_comment = await github_client.get_bot_last_comment(issue.comments_url)
        previous_review_text = last_comment[
            'body'] if last_comment else "I don't have a record of my previous review, but I'll take a fresh look!"

        pr_details_dict = await github_client.get_pr_details(repo.full_name, issue.number)
        if pr_details_dict:
            from .models import PullRequest, Repository, PREventPayload
            pr_details = PullRequest(**pr_details_dict)
            repo_payload = pr_details_dict.get('base', {}).get('repo', {})
            reconstructed_payload = PREventPayload(
                action="synchronize",
                pull_request=pr_details,
                repository=Repository(**repo_payload)
            )
            await handle_pull_request_event(reconstructed_payload, installation_id, force_review=True,
                                            previous_review=previous_review_text)
