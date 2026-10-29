from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from analytics import answer_question, initialize_database

app = FastAPI(title="Mini AI Business Intelligence Assistant", version="1.0.0")

class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)

@app.on_event("startup")
def startup():
    initialize_database()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/ask")
def ask(request: QuestionRequest):
    try:
        result = answer_question(request.question)
        if not result["ok"]:
            raise HTTPException(status_code=400, detail=result)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to process question safely.") from exc
