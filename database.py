from sqlalchemy import create_engine, Column, Integer, String, Boolean, Date, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import date

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

# Database Setup
DB_URL = "sqlite:///./productivity_app.db"
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    
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
