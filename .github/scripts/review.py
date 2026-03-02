import os
import sys
from google import genai
from github import Github, Auth

def main():
    # --- Configuration & Auth ---
    api_key = os.getenv("GEMINI_API_KEY")
    github_token = os.getenv("GITHUB_TOKEN")
    repo_name = os.getenv("REPO")
    pr_number = os.getenv("PR_NUMBER")

    if not all([api_key, github_token, repo_name, pr_number]):
        print("Error: Missing required environment variables.")
        sys.exit(1)

    # Initialize Modern Gemini Client
    client = genai.Client(api_key=api_key)
    # Note: Ensure this model name is active in your AI Studio
    model_id = "gemini-1.5-pro" 

    # Initialize GitHub with modern Auth (Fixes DeprecationWarning)
    auth = Auth.Token(github_token)
    g = Github(auth=auth)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(int(pr_number))

    # --- Build Diff ---
    changed_files = pr.get_files()
    diff_sections = []

    for f in changed_files:
        if f.patch:
            diff_sections.append(f"### File: {f.filename}\n```diff\n{f.patch}\n```")

    if not diff_sections:
        print("No text changes found, skipping review.")
        return

    full_diff = "\n\n".join(diff_sections)

    # --- Prompt ---
    prompt = f"""
You are a senior code reviewer. Review the following Pull Request diff.

**PR Title:** {pr.title}
**PR Description:** {pr.body or 'No description provided'}

---
**Changed Files & Diffs:**
{full_diff}
---

Provide a summary, potential bugs, suggestions, and an assessment (Approve/Request Changes).
"""

    # --- Generate Review & Post ---
    try:
        print(f"Generating review for PR #{pr_number}...")
        # Modern SDK call
        response = client.models.generate_content(
            model=model_id,
            contents=prompt
        )
        
        review_comment = response.text

        # Post comment
        pr.create_issue_comment(f"## 🤖 Gemini Code Review\n\n{review_comment}")
        print("Review comment posted successfully.")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
