import os
import sys
from google.adk.agents import Agent
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from mcp import StdioServerParameters
from google.adk.runners import InMemoryRunner

def main():
    terraform_connection = StdioConnectionParams(
        server_params=StdioServerParameters(
            command="npx",
            args=["-y", "hashicorp/terraform-mcp-server"]
        )
    )

    try:
        terraform_tools = McpToolset(connection_params=terraform_connection)
    except Exception as e:
        print(f"## ⚠️ MCP Initialization Error\nFailed to start tools: {e}")
        sys.exit(1)

    reviewer_agent = Agent(
        name="GCP_PR_Reviewer",
        model="gemini-2.5-pro",
        instruction="""
        You are an expert Google Cloud Platform (GCP) Security Architect. 
        Review the proposed Terraform code via a git diff using your MCP tools.
        
        If the code contains syntax errors, typos (like misspelled resource blocks), or security flaws:
        1. You MUST include the exact word [REJECTED] at the top of your response.
        2. Explain what is wrong.
        
        If the code is perfect:
        1. You MUST include the exact word [APPROVED] at the top of your response.
        """,
        tools=[terraform_tools]
    )

    diff_content = "No diff provided."
    if os.path.exists("pr_diff.txt"):
        with open("pr_diff.txt", "r") as f:
            diff_content = f.read()
    
    # Send status to stderr so it doesn't get put in the PR comment
    print("Agent is analyzing the git diff...", file=sys.stderr)
    
    runner = InMemoryRunner(agent=reviewer_agent)
    prompt = f"Please review this Terraform git diff:\n\n{diff_content}"
    
    events = runner.run(
        user_id="github", 
        session_id="pr_review", 
        new_message=prompt
    )
    
    full_response = ""
    for event in events:
        if hasattr(event, 'is_final_response') and event.is_final_response():
             if hasattr(event, 'content') and event.content and event.content.parts:
                 full_response = event.content.parts[0].text
                 print(full_response)
        elif hasattr(event, 'actions') and getattr(event.actions, 'escalate', None):
             print(f"## ⚠️ AI Error\n{getattr(event, 'error_message', 'Unknown error')}")
             sys.exit(1)

    # 1. THE SAFETY NET: Prevent empty files
    if not full_response.strip():
        print("## ⚠️ AI Review Error\nThe agent failed to generate a review. The response was empty.")
        sys.exit(1)

    # 2. THE GATEKEEPER: Check if the AI rejected the code
    if "[REJECTED]" in full_response.upper():
        print("\n\nReview complete. Errors found. Failing the pipeline.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
