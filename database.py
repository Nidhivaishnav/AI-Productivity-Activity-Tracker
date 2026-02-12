from sqlalchemy import create_engine, Column, Integer, String, Boolean, Date, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import date
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Try to get secrets from Streamlit Cloud, fallback to .env
def get_secret(key, default=None):
    """Get secret from Streamlit Cloud or environment variable"""
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, default)

Base = declarative_base()

class Goal(Base):
    __tablename__ = 'goals'
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String)
    target_date = Column(Date)
    progress = Column(Float, default=0.0)
    is_completed = Column(Boolean, default=False)
    
    tasks = relationship("Task", back_populates="goal", cascade="all, delete-orphan")

class Task(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True)
    goal_id = Column(Integer, ForeignKey('goals.id'), nullable=True)
    title = Column(String, nullable=False)
    description = Column(String)
    due_date = Column(Date, default=date.today)
    status = Column(String, default="Pending") # Pending, In Progress, Completed
    priority = Column(Integer, default=1) # 1: Low, 2: Medium, 3: High
    difficulty = Column(Integer, default=1) # 1-5
    
    goal = relationship("Goal", back_populates="tasks")
    category = Column(String, default="General") # General, Learning, Coding, Health, etc.
    time_spent = Column(Integer, default=0) # Saved in seconds
    reminder_time = Column(String, nullable=True) # ISO format datetime string

class UserStats(Base):
    __tablename__ = 'user_stats'
    id = Column(Integer, primary_key=True)
    date = Column(Date, unique=True)
    tasks_completed = Column(Integer, default=0)
    productivity_score = Column(Float, default=0.0)
    streak_count = Column(Integer, default=0)

class Badge(Base):
    __tablename__ = 'badges'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    description = Column(String)
    icon = Column(String)
    unlocked_at = Column(Date, nullable=True)

# Database Setup - Use Supabase PostgreSQL or fallback to SQLite
SUPABASE_DB_URL = get_secret("SUPABASE_DB_URL")

if SUPABASE_DB_URL:
    DB_URL = SUPABASE_DB_URL
    engine = create_engine(DB_URL, pool_pre_ping=True)
else:
    # Fallback to SQLite for local development
    DB_URL = "sqlite:///./productivity_app.db"
    engine = create_engine(DB_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    
    # Migration: Check if new columns exist in tasks table
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    
    try:
        columns = [c['name'] for c in inspector.get_columns('tasks')]
        
        with engine.connect() as conn:
            if 'category' not in columns:
                try:
                    conn.execute(text("ALTER TABLE tasks ADD COLUMN category VARCHAR DEFAULT 'General'"))
                except Exception:
                    pass  # Column might already exist
            
            if 'time_spent' not in columns:
                try:
                    conn.execute(text("ALTER TABLE tasks ADD COLUMN time_spent INTEGER DEFAULT 0"))
                except Exception:
                    pass
                
            if 'reminder_time' not in columns:
                try:
                    conn.execute(text("ALTER TABLE tasks ADD COLUMN reminder_time VARCHAR NULL"))
                except Exception:
                    pass
                
            conn.commit()
    except Exception:
        pass  # Table might not exist yet on first run
    
    # Initialize some default badges if they don't exist
    session = SessionLocal()
    if session.query(Badge).count() == 0:
        badges = [
            Badge(name="First Step", description="Complete your first task", icon="🌟"),
            Badge(name="Early Bird", description="Complete a task before 8 AM", icon="🌅"),
            Badge(name="Consistency King", description="Maintain a 7-day streak", icon="🔥"),
            Badge(name="Task Master", description="Complete 50 tasks", icon="🏆"),
            Badge(name="Goal Getter", description="Complete your first long-term goal", icon="🎯")
        ]
        session.add_all(badges)
        session.commit()
    session.close()
