import os
import sys
import traceback

from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams


def main():
    try:
        # =====================================================
        # MCP CONNECTION (Terraform MCP via npx)
        # =====================================================
        terraform_connection = StdioConnectionParams(
            server_params={
                "command": "npx",
                "args": ["-y", "hashicorp/terraform-mcp-server"],
            }
        )

        terraform_tools = McpToolset(connection_params=terraform_connection)

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
        if not os.path.exists("pr_diff.txt"):
            print("## ⚠️ No PR diff found.")
            sys.exit(1)

        with open("pr_diff.txt", "r") as f:
            diff_content = f.read()

        if not diff_content.strip():
            print("## ⚠️ PR diff is empty.")
            sys.exit(1)

        prompt_text = f"""
Please review the following Terraform git diff:

{diff_content}
"""

        runner = InMemoryRunner(agent=reviewer_agent)

        events = runner.run(
            user_id="github",
            session_id="pr_review",
            new_message=prompt_text,
        )

        full_response = ""

        for event in events:
            if hasattr(event, "is_final_response") and event.is_final_response():
                if event.content and event.content.parts:
                    full_response = event.content.parts[0].text

        if not full_response.strip():
            print("## ⚠️ AI returned empty response.")
            sys.exit(1)

        # Print response (this becomes PR comment)
        print(full_response)

        # =====================================================
        # GATEKEEPER
        # =====================================================
        if "[REJECTED]" in full_response.upper():
            sys.exit(1)

    except Exception:
        print("## ⚠️ AI crashed\n")
        print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
