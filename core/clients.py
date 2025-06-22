# core/clients.py
import httpx
import base64
import yaml
from typing import Optional, List, Dict, Any
from . import config

class GitHubClient:
    def __init__(self, token: str):
        self.headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}

    async def _make_request(self, method: str, url: str, **kwargs) -> Optional[Any]:
        final_headers = self.headers.copy()
        if 'headers' in kwargs:
            passed_headers = kwargs.pop('headers')
            final_headers.update(passed_headers)
        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                response = await client.request(method, url, headers=final_headers, **kwargs)
                response.raise_for_status()
                if response.status_code == 204: return ""
                if response.headers.get("content-type", "").startswith("application/json"): return response.json()
                return response.text
            except httpx.HTTPStatusError as e:
                print(f"❌ HTTP Error for {method} {url}: {e.response.status_code} - {e.response.text}")
                return None

    async def get_bot_last_comment(self, comments_url: str) -> Optional[Dict]:
        comments = await self._make_request("GET", comments_url)
        if comments is None: return None
        bot_comments = [c for c in comments if c.get("user", {}).get("login") == f"{config.BOT_NAME}[bot]"]
        return bot_comments[-1] if bot_comments else None

    async def get_pr_files(self, repo_full_name: str, pr_number: int) -> Optional[List[Dict]]:
        url = f"https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}/files"
        return await self._make_request("GET", url)

    async def get_file_content(self, contents_url: str) -> Optional[str]:
        file_data = await self._make_request("GET", contents_url)
        if file_data and file_data.get("encoding") == "base64":
            return base64.b64decode(file_data['content']).decode('utf-8')
        return None

    async def get_repo_secret(self, repo_full_name: str, secret_name: str) -> Optional[str]:
        # This is a placeholder. Real apps need to use the Actions API or other secure methods.
        print(f"🤫 (Simulated) Checking for repo secret '{secret_name}' in '{repo_full_name}'.")
        return None  # In a real app, this would make an authenticated API call.

    async def get_config_file(self, repo_full_name: str) -> Optional[Dict]:
        url = f"https://api.github.com/repos/{repo_full_name}/contents/.github/pullrider.yml"
        config_data = await self._make_request("GET", url)
        if config_data and config_data.get("encoding") == "base64":
            content = base64.b64decode(config_data['content']).decode('utf-8')
            return yaml.safe_load(content)
        return None

    async def get_pr_details(self, repo_full_name: str, pr_number: int) -> Optional[dict]:
        url = f"https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}"
        return await self._make_request("GET", url)

    async def post_comment(self, url: str, body: str):
        return await self._make_request("POST", url, json={"body": body})

    async def get_pr_diff(self, url: str):
        diff_headers = {"Accept": "application/vnd.github.v3.diff"}
        return await self._make_request("GET", url, headers=diff_headers)

    async def close_issue(self, repo_full_name: str, issue_number: int):
        url = f"https://api.github.com/repos/{repo_full_name}/issues/{issue_number}"
        return await self._make_request("PATCH", url, json={"state": "closed"})


class GeminiClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={self.api_key}"

    async def _call_gemini(self, prompt: str):
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        async with httpx.AsyncClient(timeout=90.0) as client:
            try:
                response = await client.post(self.api_url, json=payload)
                response.raise_for_status()
                result = response.json()
                print("✅ AI analysis successful.")
                return result['candidates'][0]['content']['parts'][0]['text']
            except Exception as e:
                print(f"❌ Failed to get analysis from Gemini: {e}")
                return "Error: Could not get a response from AI."

    async def analyze_code_with_context(self, pr_title: str, diff: str, file_contexts: Dict[str, str],
                                        custom_rules: Optional[List[str]]):
        context_str = "\n\n".join(
            f"--- Full content of `{filename}` ---\n```\n{content}\n```" for filename, content in file_contexts.items())
        rules_str = "\n".join(f"- {rule}" for rule in custom_rules) if custom_rules else "No custom rules provided."

        prompt = (
            "You are PullRider, an expert developer with a friendly, sassy personality reviewing a PR. "
            "Analyze the code based on general best practices AND the user's custom rules.\n\n"
            f"**PR Title:** \"{pr_title}\"\n\n"
            f"**Custom Rules to Enforce:**\n{rules_str}\n\n"
            f"**Full File Contexts:**\n{context_str}\n\n"
            f"**Code Diff:**\n```diff\n{diff}\n```\n\n"
            "Your task: Provide a concise, human-like review. Summarize the change, praise good work, and offer actionable suggestions if you see issues related to the custom rules or general best practices. Keep it friendly and to the point."
        )
        return await self._call_gemini(prompt)

    async def follow_up_review(self, pr_title: str, new_diff: str, previous_review: str):
        prompt = (
            "You are PullRider, doing a follow-up review on a PR. The user has made updates after your first review.\n\n"
            f"**PR Title:** \"{pr_title}\"\n\n"
            f"**Your PREVIOUS Review:**\n---\n{previous_review}\n---\n\n"
            f"**The NEW Diff with their latest changes:**\n```diff\n{new_diff}\n```\n\n"
            "Your Task: Compare the new diff to your previous review.\n"
            "1. Acknowledge their updates. (e.g., 'Hey, thanks for the updates!')\n"
            "2. Check if they addressed your main suggestions. If they did, praise them! (e.g., 'Nice, I see you fixed the loop issue.')\n"
            "3. If any major suggestions are still unaddressed, gently remind them.\n"
            "4. Briefly review the new changes for any new issues.\n"
            "Keep it short, friendly, and conversational."
        )
        return await self._call_gemini(prompt)

    async def classify_issue(self, title: str, body: Optional[str]) -> str:
        issue_text = f"Title: {title}\nBody: {body or 'No content'}"
        prompt = (
            "You are a triage bot. Classify the following GitHub issue into ONE of the following categories: "
            "`Bug Report`, `Feature Request`, `Question`, `Social`, `Spam/Unclear`. "
            "Only return the category name and nothing else.\n\n"
            f"ISSUE:\n---\n{issue_text}"
        )
        response = await self._call_gemini(prompt)
        category = response.replace("`", "").strip()
        print(f"🤖 AI Triage classified issue as: '{category}'")
        return category

    async def get_social_reply(self, issue_title: str, user_login: str) -> str:
        prompt = (
            f"You are a witty and friendly AI bot named PullRider. A user named '{user_login}' created a GitHub issue with the title '{issue_title}'. "
            "This is not a real bug report, just a social comment. "
            "Write a short, fun, human-like reply. If they ask your name, tell them. If they say hi, say hi back. Keep it brief and friendly, then say you're closing the issue to keep things tidy."
        )
        return await self._call_gemini(prompt)

    async def get_issue_quality_analysis(self, title: str, body: Optional[str]):
        issue_text = f"Title: {title}\n\nBody:\n{body or 'No description provided.'}"
        prompt = (
            "You are an expert project manager. Analyze the quality of the following GitHub issue. "
            "If it's low-quality or vague, provide specific, friendly suggestions on how to improve it. "
            "If it's a well-written issue, praise the user for the clear report.\n\n"
            f"ISSUE:\n---\n{issue_text}"
        )
        return await self._call_gemini(prompt)

