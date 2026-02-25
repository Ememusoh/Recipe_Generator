# app/agent_setup.py

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain.tools import tool
from langchain_core.prompts import PromptTemplate

# Load API keys from .env
load_dotenv(override=True)

# 1) LLM
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 2) Tavily search tool
tavily_tool = TavilySearchResults(max_results=5)


def _clean_text(text, max_len: int = 300) -> str:
    """Normalize whitespace and trim text length."""
    if not text:
        return ""
    text = " ".join(str(text).split())
    return text[:max_len]


def _score_result(result: dict, query: str) -> int:
    """
    Heuristic ranking:
    - prefer recipe/instruction pages
    - avoid noisy social pages
    - reward query term overlap
    """
    text = (
        (result.get("title", "") or "")
        + " "
        + (result.get("content", "") or "")
        + " "
        + (result.get("url", "") or "")
    ).lower()

    q = (query or "").lower()
    score = 0

    good_words = [
        "recipe",
        "recipes",
        "instructions",
        "directions",
        "how to make",
        "method",
        "allrecipes",
        "foodnetwork",
        "bbcgoodfood",
        "simplyrecipes",
    ]
    for word in good_words:
        if word in text:
            score += 2

    bad_words = ["pinterest", "tiktok", "facebook", "instagram"]
    for word in bad_words:
        if word in text:
            score -= 2

    parts = q.replace(",", " ").split()
    ignore = {"recipe", "using", "with", "and", "step", "by", "instructions", "the"}
    for p in parts:
        if len(p) < 3 or p in ignore:
            continue
        if p in text:
            score += 1

    return score


@tool
def recipe_search(query: str) -> str:
    """
    Search the web for recipe ideas and return a compact ranked list.
    The agent will choose ONE recipe from these results.
    """
    try:
        raw = tavily_tool.invoke({"query": query})
    except Exception as e:
        return f"Search failed: {e}"

    if isinstance(raw, dict) and "results" in raw:
        results = raw["results"]
    elif isinstance(raw, list):
        results = raw
    else:
        return _clean_text(raw, max_len=1000)

    if not results:
        return "No search results found."

    scored = []
    for r in results:
        if isinstance(r, dict):
            scored.append((r, _score_result(r, query)))

    scored.sort(key=lambda x: x[1], reverse=True)

    # Keep top 2 for choice, but final answer must choose ONLY ONE
    best_results = [item[0] for item in scored[:2]]

    output_lines = []
    for i, r in enumerate(best_results, start=1):
        title = _clean_text(r.get("title", "Recipe"), 120)
        url = r.get("url", "")
        snippet = _clean_text(r.get("content", ""), 320)

        output_lines.append(
            f"Result {i}\n"
            f"Title: {title}\n"
            f"URL: {url}\n"
            f"Snippet: {snippet}\n"
        )

    return "\n".join(output_lines)


tools = [recipe_search]

# 3) Custom ReAct prompt (IMPORTANT: actually includes your instructions)
recipe_system_message = """
You are a helpful cooking assistant.

Users provide ingredients they already have.
You must use the recipe_search tool at least once, then choose ONE real recipe from the tool results.

Hard requirements for the final answer:
- Recommend exactly ONE recipe (not two or more).
- Provide a clear step-by-step cooking process.
- Include a Sources section with title + URL from the tool results only.
- If some small ingredients are missing (salt, oil, pepper), mention them as optional.
- If tool snippets are limited, say the steps are approximate and still provide the best possible method + source link.
- Do not ask the user to click links without also giving steps in your response.
- Do not return alternatives.

Return this exact format:

Recipe: <recipe name>

Why this recipe:
- <short reason>

Ingredients used:
- <ingredient>
- <ingredient>

Optional pantry items:
- <item>
- <item>

Step-by-step instructions:
1. ...
2. ...
3. ...

Sources:
- <Title> (<URL>)
"""

react_template = """{system_message}

You have access to the following tools:
{tools}

Use the following format:

Question: the input question you must answer
Thought: think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat)
Thought: I now know the final answer
Final Answer: the final answer to the user

Question: {input}
Thought:{agent_scratchpad}
"""

prompt = PromptTemplate.from_template(react_template).partial(
    system_message=recipe_system_message
)

# 4) Build agent
agent = create_react_agent(llm, tools, prompt)

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=False,
    max_iterations=4,
    handle_parsing_errors=True,
)