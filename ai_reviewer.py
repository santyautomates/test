import os
import sys
import traceback

from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams


def main():
    try:
        if not os.getenv("GOOGLE_API_KEY"):
            print("## ⚠️ GOOGLE_API_KEY is not set.")
            sys.exit(1)

        if not os.path.exists("pr_diff.txt"):
            print("## ⚠️ No PR diff found.")
            sys.exit(1)

        with open("pr_diff.txt", "r") as f:
            diff_content = f.read()

        if not diff_content.strip():
            print("## ⚠️ PR diff is empty.")
            sys.exit(1)

        # ✅ USE DOCKER MCP (NOT NPX)
        terraform_tools = []
        try:
            terraform_toolset = McpToolset(
                connection_params=StdioConnectionParams(
                    server_params={
                        "command": "docker",
                        "args": [
                            "run",
                            "-i",
                            "--rm",
                            "hashicorp/terraform-mcp-server:latest",
                        ],
                    }
                )
            )

            terraform_tools, _ = terraform_toolset.get_tools()

        except Exception:
            print("⚠️ MCP failed. Continuing without MCP tools.")
            terraform_tools = []

        reviewer_agent = Agent(
            name="GCP_PR_Reviewer",
            model="gemini-2.5-flash",
            instruction="""
You are a GCP Security Architect reviewing Terraform code.

If you detect:
- Syntax errors
- Security risks
- Public access
- Hardcoded secrets
- Overly permissive IAM

Start with EXACTLY: [REJECTED]

If safe:
Start with EXACTLY: [APPROVED]
""",
            tools=terraform_tools,
        )

        prompt_text = f"""
Review this Terraform git diff:

{diff_content}
"""

        runner = InMemoryRunner(agent=reviewer_agent)

        full_response = ""

        # ✅ NORMAL LOOP (NOT ASYNC)
        for event in runner.run(
            user_id="github",
            session_id="pr_review",
            new_message=prompt_text,
        ):
            if hasattr(event, "is_final_response") and event.is_final_response():
                if event.content and event.content.parts:
                    full_response = event.content.parts[0].text
                    break

        if not full_response.strip():
            print("## ⚠️ AI returned empty response.")
            sys.exit(1)

        print(full_response)

        if "[REJECTED]" in full_response.upper():
            sys.exit(1)

    except Exception:
        print("## ⚠️ AI crashed:\n")
        print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
