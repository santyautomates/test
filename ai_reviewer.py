import os
import sys
from google.adk.agents import Agent
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from mcp import StdioServerParameters
from google.adk.runners import InMemoryRunner # <-- Import the Runner

def main():
    # 1. Connect to the MCP server
    terraform_connection = StdioConnectionParams(
        server_params=StdioServerParameters(
            command="npx",
            args=["-y", "hashicorp/terraform-mcp-server"]
        )
    )

    try:
        terraform_tools = McpToolset(connection_params=terraform_connection)
    except Exception as e:
        print(f"Failed to initialize MCP toolset: {e}")
        sys.exit(1)

    # 2. Create the Agent
    reviewer_agent = Agent(
        name="GCP_PR_Reviewer",
        model="gemini-2.5-pro",
        instruction="""
        You are an expert Google Cloud Platform (GCP) Security Architect. 
        Your job is to review proposed Terraform code. 
        You MUST use your MCP tools to check the official 'hashicorp/google' 
        provider schemas to ensure the code is valid and uses up-to-date syntax.
        Focus your review on security best practices (IAM, public access, encryption).
        Output your review in clean Markdown format.
        """,
        tools=[terraform_tools]
    )

    # 3. Get the prompt from the environment
    pr_context = os.environ.get("PR_CONTEXT", "Please review the general GCP Terraform setup.")
    
    print("Agent is querying the Terraform Registry and analyzing the code...")
    
    # 4. Execute the agent using the InMemoryRunner
    runner = InMemoryRunner(agent=reviewer_agent)
    
    # The runner executes the agent and returns a stream of events
    events = runner.run(
        user_id="github_actions", 
        session_id="pr_review_session", 
        new_message=f"Please review this context and suggest improvements: {pr_context}"
    )
    
    # Loop through the events to capture and print the text response
    for event in events:
        if hasattr(event, 'is_final_response') and event.is_final_response():
             if hasattr(event, 'content') and event.content and event.content.parts:
                 print(event.content.parts[0].text)
        elif hasattr(event, 'text') and event.text:
             print(event.text, end="", flush=True)

if __name__ == "__main__":
    main()
