import os
import sys
import google.generativeai as genai
from github import Github

def main():
    # --- Configuration & Auth ---
    # Fetch environment variables
    api_key = os.getenv("GEMINI_API_KEY")
    github_token = os.getenv("GITHUB_TOKEN")
    repo_name = os.getenv("REPO")
    pr_number = os.getenv("PR_NUMBER")

    if not all([api_key, github_token, repo_name, pr_number]):
        print("Error: Missing required environment variables.")
        sys.exit(1)

    # Initialize Gemini
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-pro")

    # Initialize GitHub
    g = Github(github_token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(int(pr_number))

    # --- Build Diff from Changed Files ---
    changed_files = pr.get_files()
    diff_sections = []

    for f in changed_files:
        if f.patch:  # Skip binary files or files with no text changes
            diff_sections.append(f"### File: {f.filename}\n```diff\n{f.patch}\n```")

    if not diff_sections:
        print("No text changes found, skipping review.")
        return

    full_diff = "\n\n".join(diff_sections)

    # --- Prompt Engineering ---
    prompt = f"""
You are a senior code reviewer. Review the following Pull Request diff.

**PR Title:** {pr.title}
**PR Description:** {pr.body or 'No description provided'}

---
**Changed Files & Diffs:**
{full_diff}
---

**Instructions:**
Please provide a high-quality review including:
1. **Summary:** A brief overview of the changes.
2. **Bugs/Issues:** Identification of logical errors, security risks, or edge cases.
3. **Suggestions:** Improvements for readability, performance, or idiomatic code.
4. **Assessment:** Clearly state: **Approve**, **Request Changes**, or **Needs Discussion**.

Be concise, professional, and use clear markdown formatting.
"""

    # --- Generate Review & Post ---
    try:
        print(f"Generating review for PR #{pr_number}...")
        response = model.generate_content(prompt)
        review_comment = response.text

        # Post the comment to the PR
        pr.create_issue_comment(f"## 🤖 Gemini Pro Code Review\n\n{review_comment}")
        print("Review comment posted successfully.")

    except Exception as e:
        print(f"Error during Gemini generation or posting: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
