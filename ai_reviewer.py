import os
import sys

from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams


def main():
    # =====================================================
    # MCP CONNECTION (Terraform MCP via npx)
    # =====================================================
    terraform_connection = StdioConnectionParams(
        server_params={
            "command": "npx",
            "args": ["-y", "hashicorp/terraform-mcp-server"]
        }
    )

    try:
        terraform_tools = McpToolset(connection_params=terraform_connection)
    except Exception as e:
        print(f"## ⚠️ MCP Initialization Error\nFailed to start tools: {e}")
        sys.exit(1)

    # =====================================================
    # AI REVIEWER AGENT
    # =====================================================
    reviewer_agent = Agent(
        name="GCP_PR_Reviewer",
        model="gemini-2.5-pro",
        instruction="""
You are an expert Google Cloud Platform (GCP) Security Architect.

You are reviewing Terraform code changes provided as a git diff.

If you detect:
- Terraform syntax errors
- Misspelled resource blocks
- Invalid arguments
- Security issues (public buckets, overly permissive IAM, etc.)
- Bad GCP architecture practices

You MUST:
1. Start your response with EXACTLY: [REJECTED]
2. Clearly explain the issues.

If everything looks correct and secure:
1. Start your response with EXACTLY: [APPROVED]
2. Briefly explain why.
""",
        tools=[terraform_tools],
    )

    # =====================================================
    # LOAD PR DIFF
    # =====================================================
    diff_content = "No diff provided."

    if os.path.exists("pr_diff.txt"):
        with open("pr_diff.txt", "r") as f:
            diff_content = f.read()

    prompt_text = f"""
Please review the following Terraform git diff:

{diff_content}
"""

    print("Agent is analyzing the git diff...", file=sys.stderr)

    runner = InMemoryRunner(agent=reviewer_agent)

    try:
        events = runner.run(
            user_id="github",
            session_id="pr_review",
            new_message=prompt_text,  # string input (CI-safe)
        )
    except Exception as e:
        print(f"## ⚠️ AI Runtime Error\n{e}")
        sys.exit(1)

    # =====================================================
    # COLLECT FINAL RESPONSE
    # =====================================================
    full_response = ""

    for event in events:
        if hasattr(event, "is_final_response") and event.is_final_response():
            if hasattr(event, "content") and event.content and event.content.parts:
                full_response = event.content.parts[0].text

    if not full_response.strip():
        print("## ⚠️ AI Review Error\nThe agent returned an empty response.")
        sys.exit(1)

    # Print response (this goes into ai_review.md)
    print(full_response)

    # =====================================================
    # GATEKEEPER LOGIC
    # =====================================================
    if "[REJECTED]" in full_response.upper():
        print("\nErrors detected. Failing pipeline.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
