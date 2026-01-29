import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain import hub
from langchain.tools import tool

# Load API keys
load_dotenv(override=True)

# 1️⃣ LLM
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 2️⃣ Tavily search tool
tavily_tool = TavilySearchResults(max_results=3)

@tool
def recipe_search(query: str) -> str:
    """Search the web for recipes and cooking instructions."""
    return tavily_tool.run(query)

tools = [recipe_search]

# 3️⃣ ReAct + Custom Prompt
base_prompt = hub.pull("hwchase17/react")

recipe_system_message = """
You are a helpful cooking assistant.

Users will provide ingredients they have.
Your job is to create a recipe using those ingredients.

When needed, use the recipe_search tool to find real recipes online.

Use the information from the tool results to write a clear step-by-step recipe.

At the end of your answer, include a section called:
Sources:
- Title (URL)
- Title (URL)

Only cite sources that actually came from the tool results.
"""

prompt = base_prompt.partial(system_message=recipe_system_message)

# 4️⃣ Build agent
agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
