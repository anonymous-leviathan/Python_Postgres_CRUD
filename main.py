from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Annotated
import models
from database import engine, SessionLocal
from sqlalchemy.orm import Session

app = FastAPI()
models.Base.metadata.create_all(bind=engine)

class ChoiceBase(BaseModel):
    choise_text: str
    is_correct: bool
    
class QuestionBase(BaseModel):
    question_text: str
    choices :List[ChoiceBase]

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
        
db_dependency = Annotated[Session, Depends(get_db)]

@app.get("/questions/{question_id}")
async def read_questions(question_id: int, db: db_dependency):
    result = db.query(models.Questions).filter(models.Questions.id == question_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Question is not found!")
    return result
    
@app.get("/choices/{question_id}")
async def read_choices(question_id: int, db: db_dependency):
    result = db.query(models.Choices).filter(models.Choices.question_id == question_id)
    if not result:
        raise HTTPException(status_code=404, detail='Choice is not found!')
    return result

@app.delete("/questions/{question_id}")
async def delete_question(question_id: int, db: db_dependency):
    # Find the question
    question = db.query(models.Questions).filter(models.Questions.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found!")
    
    # Find and delete the associated choices
    choices = db.query(models.Choices).filter(models.Choices.question_id == question_id)
    if choices.count() > 0:
        choices.delete(synchronize_session=False)

    # Delete the question itself
    db.delete(question)
    db.commit()

    return {"message": f"Question {question_id} and associated choices have been deleted."}


@app.delete("/choices/{choice_id}")
async def delete_choice(choice_id: int, db: db_dependency):
    # Find the choice
    choice = db.query(models.Choices).filter(models.Choices.id == choice_id).first()
    if not choice:
        raise HTTPException(status_code=404, detail="Choice not found!")
    
    # Delete the choice
    db.delete(choice)
    db.commit()

    return {"message": f"Choice {choice_id} has been deleted."}


@app.get("/questions", response_model=List[QuestionBase])
async def get_all_questions(db: db_dependency):
    questions = db.query(models.Questions).all()
    
    if not questions:
        raise HTTPException(status_code=404, detail="No questions found")
    
    # Retrieve choices for each question
    all_questions = []
    for question in questions:
        choices = db.query(models.Choices).filter(models.Choices.question_id == question.id).all()
        question_with_choices = {
            "question_text": question.question_text,
            "choices": [{"choise_text": choice.choice_text, "is_correct": choice.is_correct} for choice in choices]
        }
        all_questions.append(question_with_choices)
    
    return all_questions


    
@app.post("/questions")
async def create_questions(question: QuestionBase, db: db_dependency):
    db_question = models.Questions(question_text=question.question_text)
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    for choice in question.choices:
        db_choice = models.Choices(choice_text=choice.choise_text, is_correct=choice.is_correct, question_id=db_question.id)
        db.add(db_choice)
    db.commit()