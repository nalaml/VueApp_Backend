from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, Column, Integer, String, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from enum import Enum as PyEnum
import logging
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Response


# Database connection
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:postgresql@localhost/taskdb"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Task status enum
class TaskStatus(str, PyEnum):
    assigned = "assigned"
    inprogress = "inprogress"
    completed = "completed"

# SQLAlchemy model
class TaskModel(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    status = Column(String, default=TaskStatus.assigned.value)

# Pydantic model for request/response
class TaskSchema(BaseModel):
    id: int
    title: str
    status: TaskStatus

    class Config:
        orm_mode = True

class TaskCreateSchema(BaseModel):
    title: str
    status: TaskStatus = TaskStatus.assigned

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8081"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.post("/add_task", response_model=TaskSchema)
def create_task(task: TaskCreateSchema, db: Session = Depends(get_db)):
    try:
        logger.info(f"Attempting to create task: {task.dict()}")
        db_task = TaskModel(title=task.title, status=task.status.value)
        db.add(db_task)
        db.commit()
        db.refresh(db_task)
        logger.info(f"Task created successfully: {db_task.__dict__}")
        return db_task
    except Exception as e:
        logger.error(f"Error creating task: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred while creating the task: {str(e)}")

@app.get("/get_tasks", response_model=list[TaskSchema])
def read_tasks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    tasks = db.query(TaskModel).offset(skip).limit(limit).all()
    return tasks

@app.get("/tasks/{task_id}", response_model=TaskSchema)
def read_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.put("/task/{task_id}", response_model=TaskSchema)
def update_task(task_id: int, task: TaskCreateSchema, db: Session = Depends(get_db)):
    try:
        db_task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        if db_task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        db_task.title = task.title
        db_task.status = task.status.value
        db.commit()
        db.refresh(db_task)
        return db_task
    except Exception as e:
        logger.error(f"Error updating task: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred while updating the task: {str(e)}")

@app.delete("/task/{task_id}", response_model=TaskSchema)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return task

@app.options("/task/{task_id}")
async def options_task(task_id: int):
    return Response(status_code=204)
    