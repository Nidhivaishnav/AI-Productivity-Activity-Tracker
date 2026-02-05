from datetime import date, timedelta
from database import SessionLocal, Task, UserStats, Badge, Goal
from sqlalchemy import func

def calculate_productivity_score(completed_tasks):
    """
    Calculates a score based on task count and difficulty.
    Formula: Sum(difficulty * weight)
    """
    if not completed_tasks:
        return 0.0
    
    score = 0
    for task in completed_tasks:
        score += task.difficulty * 10
    
    return min(score, 100.0) # Cap at 100

def update_daily_stats():
    session = SessionLocal()
    today = date.today()
    
    # Get completed tasks for today
    completed_tasks = session.query(Task).filter(
        Task.status == "Completed",
        Task.due_date == today
    ).all()
    
    count = len(completed_tasks)
    score = calculate_productivity_score(completed_tasks)
    
    # Update or create UserStats for today
    stats = session.query(UserStats).filter(UserStats.date == today).first()
    if not stats:
        # Check yesterday for streak
        yesterday = today - timedelta(days=1)
        yesterday_stats = session.query(UserStats).filter(UserStats.date == yesterday).first()
        streak = (yesterday_stats.streak_count + 1) if (yesterday_stats and yesterday_stats.tasks_completed > 0) else (1 if count > 0 else 0)
        
        stats = UserStats(date=today, tasks_completed=count, productivity_score=score, streak_count=streak)
        session.add(stats)
    else:
        stats.tasks_completed = count
        stats.productivity_score = score
        # Streak logic might need a bit more care on updates, but for now:
        if stats.tasks_completed > 0 and stats.streak_count == 0:
             yesterday = today - timedelta(days=1)
             yesterday_stats = session.query(UserStats).filter(UserStats.date == yesterday).first()
             stats.streak_count = (yesterday_stats.streak_count + 1) if yesterday_stats else 1

    session.commit()
    check_badges(session, stats)
    session.close()

def check_badges(session, stats):
    """
    Unlocks badges based on performance.
    """
    # First Step
    if stats.tasks_completed >= 1:
        badge = session.query(Badge).filter(Badge.name == "First Step").first()
        if badge and not badge.unlocked_at:
            badge.unlocked_at = date.today()

    # Consistency King (7 day streak)
    if stats.streak_count >= 7:
        badge = session.query(Badge).filter(Badge.name == "Consistency King").first()
        if badge and not badge.unlocked_at:
            badge.unlocked_at = date.today()

    # Task Master (50 total)
    total_completed = session.query(func.sum(UserStats.tasks_completed)).scalar() or 0
    if total_completed >= 50:
        badge = session.query(Badge).filter(Badge.name == "Task Master").first()
        if badge and not badge.unlocked_at:
            badge.unlocked_at = date.today()

    session.commit()

def forecast_productivity():
    """
    Uses Linear Regression to predict productivity score for tomorrow 
    based on the last 7 days of data.
    """
    from sklearn.linear_model import LinearRegression
    import numpy as np
    
    session = SessionLocal()
    # Get last 14 days of data
    stats = session.query(UserStats).order_by(UserStats.date.desc()).limit(14).all()
    session.close()
    
    if len(stats) < 3:
        return None # Not enough data for a trend
    
    # Reverse to get chronological order
    stats = stats[::-1]
    
    # X = days (0, 1, 2...), y = productivity_score
    X = np.array(range(len(stats))).reshape(-1, 1)
    y = np.array([s.productivity_score for s in stats])
    
    model = LinearRegression()
    model.fit(X, y)
    
    # Predict for tomorrow
    next_day = np.array([[len(stats)]])
    prediction = model.predict(next_day)[0]
    
    return max(0.0, min(100.0, float(prediction)))

def get_productivity_trends():
    """
    Returns data for Plotly charts.
    """
    session = SessionLocal()
    stats = session.query(UserStats).order_by(UserStats.date.asc()).all()
    session.close()
    
    dates = [s.date for s in stats]
    scores = [s.productivity_score for s in stats]
    counts = [s.tasks_completed for s in stats]
    
    return dates, scores, counts
