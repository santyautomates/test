import os
import sys
import asyncio
import traceback

from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams


async def main():
    try:
        # =====================================================
        # LOAD PR DIFF FIRST (fail fast before spinning up MCP)
        # =====================================================
        if not os.path.exists("pr_diff.txt"):
            print("## ⚠️ No PR diff found. Expected a file named `pr_diff.txt`.")
            sys.exit(1)

        with open("pr_diff.txt", "r") as f:
            diff_content = f.read()

        if not diff_content.strip():
            print("## ⚠️ PR diff is empty. Nothing to review.")
            sys.exit(1)

        # =====================================================
        # MCP CONNECTION (Terraform MCP via npx)
        # =====================================================
        terraform_connection = StdioConnectionParams(
            server_params={
                "command": "npx",
                "args": ["-y", "@hashicorp/terraform-mcp-server"],
            }
        )

        # McpToolset must be used as an async context manager
        async with McpToolset(connection_params=terraform_connection) as terraform_tools:

            # =====================================================
            # AI REVIEWER AGENT
            # =====================================================
            reviewer_agent = Agent(
                name="GCP_PR_Reviewer",
                model="gemini-2.5-flash",
                instruction="""
You are an expert Google Cloud Platform (GCP) Security Architect.
You are reviewing Terraform code changes provided as a git diff.

If you detect ANY of the following:
- Terraform syntax errors
- Misspelled resource blocks or invalid arguments
- Security issues (public buckets, overly permissive IAM, open firewall rules, etc.)
- Hardcoded secrets or credentials
- Bad GCP architecture practices

You MUST:
1. Start your response with EXACTLY: [REJECTED]
2. Clearly explain each issue found with the relevant line/block from the diff.

If everything looks correct and secure:
1. Start your response with EXACTLY: [APPROVED]
2. Briefly explain why the changes are acceptable.

Always be specific and reference the actual diff content in your review.
""",
                tools=[terraform_tools],
            )

            # =====================================================
            # BUILD PROMPT
            # =====================================================
            prompt_text = f"""
Please review the following Terraform git diff for GCP security issues,
syntax errors, bad practices, and architectural concerns:

{diff_content}
"""

            # =====================================================
            # RUN AGENT (async)
            # =====================================================
            runner = InMemoryRunner(agent=reviewer_agent)

            full_response = ""

            async for event in runner.run(
                user_id="github",
                session_id="pr_review",
                new_message=prompt_text,
            ):
                if hasattr(event, "is_final_response") and event.is_final_response():
                    if event.content and event.content.parts:
                        full_response = event.content.parts[0].text
                        break  # We have what we need

            # =====================================================
            # VALIDATE RESPONSE
            # =====================================================
            if not full_response.strip():
                print("## ⚠️ AI returned an empty response. This may be a quota or API key issue.")
                sys.exit(1)

            # Print response — this becomes the PR comment via ai_review.md
            print(full_response)

            # =====================================================
            # GATEKEEPER — exit 1 blocks the PR merge
            # =====================================================
            if "[REJECTED]" in full_response.upper():
                sys.exit(1)

    except Exception:
        print("## ⚠️ AI Reviewer crashed with an unexpected error:\n")
        print("```")
        print(traceback.format_exc())
        print("```")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
