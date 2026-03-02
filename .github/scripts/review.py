import os
import sys
import json
import re
from google import genai
from github import Github, Auth

def main():
    # --- Configuration & Auth ---
    api_key = os.getenv("GEMINI_API_KEY")
    github_token = os.getenv("GITHUB_TOKEN")
    repo_name = os.getenv("REPO")
    pr_number = os.getenv("PR_NUMBER")

    client = genai.Client(api_key=api_key)
    model_id = "gemini-2.0-flash" # Use a stable 2026 model

    g = Github(auth=Auth.Token(github_token))
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(int(pr_number))

    # --- Build Diff ---
    changed_files = pr.get_files()
    diff_sections = []
    for f in changed_files:
        if f.patch:
            diff_sections.append(f"### File: {f.filename}\n{f.patch}")

    if not diff_sections:
        return

    full_diff = "\n\n".join(diff_sections)

    # --- Prompt for JSON Output ---
    prompt = f"""
    Review the following PR diff. You MUST respond with a JSON object.
    
    Format:
    {{
      "summary": "Brief overall summary",
      "suggestions": [
        {{ "path": "filename.py", "line": 10, "comment": "comment text" }}
      ]
    }}

    Diff:
    {full_diff}
    """

    try:
        response = client.models.generate_content(model=model_id, contents=prompt)
        # Extract JSON from response (handling potential markdown blocks)
        raw_text = re.search(r'\{.*\}', response.text, re.DOTALL).group()
        data = json.loads(raw_text)

        # 1. Post Summary as a high-level comment
        pr.create_issue_comment(f"## 🤖 Gemini Summary\n\n{data.get('summary')}")

        # 2. Prepare Line-Wise Comments
        # We use the latest commit SHA to attach comments to the right version
        commit = list(pr.get_commits())[-1]
        
        comments = []
        for sug in data.get('suggestions', []):
            comments.append({
                "path": sug['path'],
                "line": int(sug['line']),
                "body": sug['comment']
            })

        # 3. Post a formal Review with line-level comments
        if comments:
            pr.create_review(commit=commit, body="Gemini found some specific areas for improvement:", event="COMMENT", comments=comments)
            print("Line-wise suggestions posted.")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
