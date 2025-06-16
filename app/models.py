import uuid
from sqlalchemy import create_engine, Column, String, Text, Boolean, ForeignKey, Float, Integer, Uuid
from sqlalchemy.orm import relationship, declarative_base

# Define the base class for declarative models
Base = declarative_base()

class Subject(Base):
    """
    SQLAlchemy model for subjects.
    Represents the subjects available, e.g., 'IPA', 'Bahasa Indonesia'.
    """
    __tablename__ = 'subjects'
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)

    questions = relationship("Question", back_populates="subject")
    task_answers = relationship("TaskAnswer", back_populates="subject")

class Student(Base):
    """
    SQLAlchemy model for students.
    Represents the students who provide answers.
    """
    __tablename__ = 'students'
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    
    task_answers = relationship("TaskAnswer", back_populates="student")

class Question(Base):
    """
    SQLAlchemy model for questions.
    Represents the questions for each subject.
    """
    __tablename__ = 'questions'
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_id = Column(Uuid(as_uuid=True), ForeignKey('subjects.id'), nullable=False)
    question_text = Column(Text, nullable=False)
    preferred_answer = Column(Text)

    subject = relationship("Subject", back_populates="questions")
    task_answers = relationship("TaskAnswer", back_populates="question")
    request_logs = relationship("RequestLog", back_populates="question")

class TaskAnswer(Base):
    """
    SQLAlchemy model for task answers.
    Represents a student's answer to a specific question.
    """
    __tablename__ = 'task_answers'
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_id = Column(Uuid(as_uuid=True), ForeignKey('subjects.id'), nullable=False)
    question_id = Column(Uuid(as_uuid=True), ForeignKey('questions.id'), nullable=False)
    student_id = Column(Uuid(as_uuid=True), ForeignKey('students.id'), nullable=False)
    answer = Column(Text, nullable=False)
    ground_truth = Column(Boolean, nullable=False)
    status = Column(Boolean, nullable=True) # This will be updated by the AI

    subject = relationship("Subject", back_populates="task_answers")
    question = relationship("Question", back_populates="task_answers")
    student = relationship("Student", back_populates="task_answers")

class RequestLog(Base):
    """
    Represents a log entry for a request made, including token counts.
    """
    __tablename__ = 'request_logs'
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_time = Column(Float, nullable=False)
    question_count = Column(Integer, nullable=False)
    prompt_token_count = Column(Integer, nullable=False)
    candidates_token_count = Column(Integer, nullable=False)
    total_token_count = Column(Integer, nullable=False)
    
    # Foreign Key to link to a specific question
    question_id = Column(Uuid(as_uuid=True), ForeignKey('questions.id'), nullable=False)
    
    # Relationship back to the Question model
    question = relationship("Question", back_populates="request_logs")

    def __repr__(self):
        return f"<RequestLog(id={self.id}, question_id={self.question_id}, duration='{self.request_time}')>"