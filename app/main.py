from fastapi import FastAPI
from pydantic import BaseModel
from app.agent_setup import agent_executor

app = FastAPI(title="Recipe RAG Agent API")

# Request model
class IngredientsRequest(BaseModel):
    ingredients: str

# API endpoint
@app.post("/generate_recipe")
async def generate_recipe(request: IngredientsRequest):
    response = agent_executor.invoke({"input": request.ingredients})
    return {"recipe": response["output"]}
