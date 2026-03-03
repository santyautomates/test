import os
import sys
from google.adk.agents import Agent
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams

def main():
    # 1. Connect to the MCP server using npx
    terraform_connection = StdioConnectionParams(
        command="npx",
        args=["-y", "hashicorp/terraform-mcp-server"]
    )

    try:
        terraform_tools = McpToolset(connection_params=terraform_connection)
    except Exception as e:
        print(f"Failed to initialize MCP toolset: {e}")
        sys.exit(1)

    # 2. Create the Agent customized for PR reviews
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

    # 3. Get the prompt from the environment (passed by GitHub Actions)
    pr_context = os.environ.get("PR_CONTEXT", "Please review the general GCP Terraform setup.")
    
    print("Agent is querying the Terraform Registry and analyzing the code...")
    
    # 4. Run the agent and output the response
    response = reviewer_agent.run(f"Please review this context and suggest improvements: {pr_context}")
    
    # Print the raw content so GitHub Actions can capture it
    print(response.content)

if __name__ == "__main__":
    main()
