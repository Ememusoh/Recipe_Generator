# app/main.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.agent_setup import agent_executor, llm

app = FastAPI(title="Recipe Assistant Chatbot API")


class IngredientsRequest(BaseModel):
    ingredients: str


REQUIRED_SECTIONS = [
    "Recipe:",
    "Why this recipe:",
    "Ingredients used:",
    "Step-by-step instructions:",
    "Sources:",
]


def _has_required_sections(text: str) -> bool:
    if not text:
        return False
    return all(section in text for section in REQUIRED_SECTIONS)


def _looks_like_multiple_recipes(text: str) -> bool:
    if not text:
        return False
    lowered = text.lower()
    # simple heuristics for "two recipe" / "either/or" responses
    bad_patterns = [
        "here are two recipes",
        "you can try either",
        "either the",
        "1.",
        "2.",
    ]
    # only flag if it seems like alternatives, not step numbering section
    if "Step-by-step instructions:" in text:
        return False
    return any(p in lowered for p in bad_patterns)


def _repair_output(ingredients: str, raw_output: str) -> str:
    """
    Fallback formatter: forces one recipe + steps + sources if the agent output drifts.
    Uses the same LLM (no extra web search).
    """
    repair_prompt = f"""
You are fixing a recipe assistant response so it matches the required format.

User ingredients:
{ingredients}

Original assistant response:
{raw_output}

Rules:
- Choose exactly ONE recipe from the original response (best fit).
- Provide step-by-step instructions.
- Include a Sources section.
- If exact instructions are not available, say they are approximate.
- Keep it concise but complete.
- Return ONLY the formatted answer below.

Required format:

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
    repaired = llm.invoke(repair_prompt)
    content = getattr(repaired, "content", None)
    return content if content else raw_output


@app.post("/generate_recipe")
async def generate_recipe(request: IngredientsRequest):
    ingredients = (request.ingredients or "").strip()

    if not ingredients:
        raise HTTPException(status_code=400, detail="Please provide ingredients.")

    try:
        user_input = (
            f"Ingredients: {ingredients}\n\n"
            "Use recipe_search first. Return EXACTLY one recipe with step-by-step instructions and sources."
        )

        response = agent_executor.invoke({"input": user_input})
        recipe_text = response.get("output", "No recipe returned.")

        # Guardrail: enforce final format if agent drifts
        if (not _has_required_sections(recipe_text)) or _looks_like_multiple_recipes(recipe_text):
            recipe_text = _repair_output(ingredients=ingredients, raw_output=recipe_text)

        return {"recipe": recipe_text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating recipe: {e}")