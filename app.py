import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
from database import init_db, SessionLocal, Task, Goal, Badge, UserStats, User, hash_password, verify_password
from logic_llm import GoalAgent
from logic_analytics import update_daily_stats, get_productivity_trends, forecast_productivity
import plotly.express as px
import plotly.graph_objects as go

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Productivity Hub",
    page_icon="🚀",
    layout="wide",
)

# Initialize Database
init_db()
update_daily_stats()

# --- Authentication ---
def show_auth_page():
    """Show login/signup page"""
    st.markdown("""
        <style>
        .auth-container {
            max-width: 420px; margin: 60px auto; padding: 40px;
            background: rgba(255,255,255,0.05); backdrop-filter: blur(20px);
            border-radius: 24px; border: 1px solid rgba(255,255,255,0.1);
        }
        .auth-title {
            text-align: center; font-size: 2rem; font-weight: 700; margin-bottom: 10px;
            background: linear-gradient(90deg, #00d4ff, #a855f7);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        .auth-subtitle { text-align: center; color: rgba(255,255,255,0.5); margin-bottom: 30px; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="auth-container">', unsafe_allow_html=True)
    st.markdown('<div class="auth-title">🚀 Productivity AI</div>', unsafe_allow_html=True)
    st.markdown('<p class="auth-subtitle">Sign in to track your goals</p>', unsafe_allow_html=True)

    auth_tab1, auth_tab2 = st.tabs(["🔑 Sign In", "✨ Sign Up"])

    with auth_tab1:
        with st.form("login_form"):
            login_user = st.text_input("Username", placeholder="Enter username", key="login_u")
            login_pass = st.text_input("Password", type="password", placeholder="Enter password", key="login_p")
            if st.form_submit_button("🔓 Sign In", use_container_width=True):
                if login_user and login_pass:
                    db = SessionLocal()
                    user = db.query(User).filter(User.username == login_user).first()
                    if user and verify_password(login_pass, user.password_hash):
                        st.session_state['user_id'] = user.id
                        st.session_state['username'] = user.username
                        db.close()
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password")
                    db.close()
                else:
                    st.warning("Please fill in all fields")

    with auth_tab2:
        with st.form("signup_form"):
            new_user = st.text_input("Username", placeholder="Choose a username", key="signup_u")
            new_email = st.text_input("Email (optional)", placeholder="your@email.com", key="signup_e")
            new_pass = st.text_input("Password", type="password", placeholder="Choose a password", key="signup_p")
            new_pass2 = st.text_input("Confirm Password", type="password", placeholder="Confirm password", key="signup_p2")
            if st.form_submit_button("🚀 Create Account", use_container_width=True):
                if new_user and new_pass:
                    if new_pass != new_pass2:
                        st.error("❌ Passwords don't match")
                    elif len(new_pass) < 4:
                        st.error("❌ Password must be at least 4 characters")
                    else:
                        db = SessionLocal()
                        existing = db.query(User).filter(User.username == new_user).first()
                        if existing:
                            st.error("❌ Username already taken")
                        else:
                            user = User(username=new_user, password_hash=hash_password(new_pass), email=new_email or None)
                            db.add(user)
                            db.commit()
                            st.session_state['user_id'] = user.id
                            st.session_state['username'] = user.username
                            st.success("🎉 Account created!")
                            db.close()
                            st.rerun()
                        db.close()
                else:
                    st.warning("Please fill in username and password")

    st.markdown('</div>', unsafe_allow_html=True)

# --- Auth Gate ---
if 'user_id' not in st.session_state:
    show_auth_page()
    st.stop()

current_user_id = st.session_state['user_id']

# --- Daily Target Reminder Notification (11 AM - 12 PM) ---
def show_daily_reminder():
    """Show reminder notification between 11 AM and 12 PM to set daily targets"""
    current_hour = datetime.now().hour
    current_date = date.today().isoformat()
    
    # Initialize session state for dismissed reminders
    if 'reminder_dismissed_date' not in st.session_state:
        st.session_state.reminder_dismissed_date = None
    
    # Check if within reminder window (11 AM - 12 PM) and not dismissed today
    is_reminder_time = 11 <= current_hour < 12
    is_dismissed_today = st.session_state.reminder_dismissed_date == current_date
    
    if is_reminder_time and not is_dismissed_today:
        # Browser notification JavaScript (requests permission and shows notification)
        st.markdown("""
            <script>
                // Request notification permission
                if ('Notification' in window && Notification.permission === 'default') {
                    Notification.requestPermission();
                }
                
                // Show browser notification if permitted
                if ('Notification' in window && Notification.permission === 'granted') {
                    // Check if notification was already shown in this session
                    if (!sessionStorage.getItem('dailyReminderShown')) {
                        new Notification('🎯 Daily Target Reminder', {
                            body: 'It\\'s time to set your daily targets! Stay focused and productive.',
                            icon: '🚀',
                            tag: 'daily-reminder'
                        });
                        sessionStorage.setItem('dailyReminderShown', 'true');
                    }
                }
            </script>
        """, unsafe_allow_html=True)
        
        # In-app animated reminder banner
        st.markdown("""
            <style>
                @keyframes reminderPulse {
                    0%, 100% { 
                        box-shadow: 0 0 20px rgba(0, 212, 255, 0.4), 0 0 40px rgba(168, 85, 247, 0.2);
                    }
                    50% { 
                        box-shadow: 0 0 30px rgba(0, 212, 255, 0.6), 0 0 60px rgba(168, 85, 247, 0.4);
                    }
                }
                @keyframes bellRing {
                    0%, 100% { transform: rotate(0deg); }
                    10%, 30%, 50% { transform: rotate(-10deg); }
                    20%, 40% { transform: rotate(10deg); }
                    60% { transform: rotate(0deg); }
                }
                .reminder-banner {
                    background: linear-gradient(135deg, rgba(168, 85, 247, 0.3) 0%, rgba(0, 212, 255, 0.3) 50%, rgba(236, 72, 153, 0.3) 100%);
                    backdrop-filter: blur(20px);
                    -webkit-backdrop-filter: blur(20px);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    border-radius: 16px;
                    padding: 20px 30px;
                    margin-bottom: 20px;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    animation: reminderPulse 2s ease-in-out infinite;
                    position: relative;
                    overflow: hidden;
                }
                .reminder-banner::before {
                    content: '';
                    position: absolute;
                    top: 0;
                    left: -100%;
                    width: 100%;
                    height: 100%;
                    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
                    animation: shimmerBanner 3s infinite;
                }
                @keyframes shimmerBanner {
                    0% { left: -100%; }
                    100% { left: 100%; }
                }
                .reminder-icon {
                    font-size: 2.5rem;
                    margin-right: 20px;
                    animation: bellRing 2s ease-in-out infinite;
                    display: inline-block;
                }
                .reminder-content {
                    flex: 1;
                }
                .reminder-title {
                    font-size: 1.3rem;
                    font-weight: 700;
                    color: #fff;
                    margin: 0 0 5px 0;
                    background: linear-gradient(90deg, #fff, #00d4ff);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                }
                .reminder-subtitle {
                    color: rgba(255, 255, 255, 0.8);
                    font-size: 0.95rem;
                    margin: 0;
                }
            </style>
            <div class="reminder-banner">
                <span class="reminder-icon">🔔</span>
                <div class="reminder-content">
                    <p class="reminder-title">⏰ Time to Set Your Daily Targets!</p>
                    <p class="reminder-subtitle">It's between 11 AM - 12 PM. Plan your day for maximum productivity!</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Action buttons
        col1, col2, col3 = st.columns([2, 1, 1])
        with col2:
            if st.button("🎯 Set Daily Targets", key="reminder_set_targets", use_container_width=True):
                st.session_state['nav_to'] = "My Tasks"
                st.rerun()
        with col3:
            if st.button("✕ Dismiss", key="reminder_dismiss", use_container_width=True):
                st.session_state.reminder_dismissed_date = current_date
                st.rerun()
        
        st.markdown("<hr style='border: 1px solid rgba(255,255,255,0.1); margin: 20px 0;'>", unsafe_allow_html=True)

def check_task_reminders():
    """Check for specific task reminders"""
    if 'shown_reminders' not in st.session_state:
        st.session_state.shown_reminders = []
        
    db = SessionLocal()
    # Get tasks with reminders set
    tasks_with_reminders = db.query(Task).filter(Task.reminder_time.isnot(None), Task.status != "Completed").all()
    
    current_time = datetime.now()
    
    for task in tasks_with_reminders:
        try:
            reminder_dt = datetime.fromisoformat(task.reminder_time)
            # Check if reminder is due (within last 15 mins) and not shown
            if reminder_dt <= current_time and task.id not in st.session_state.shown_reminders:
                if (current_time - reminder_dt).total_seconds() < 900: # 15 mins window
                    st.toast(f"🔔 Reminder: {task.title}", icon="⏰")
                    st.session_state.shown_reminders.append(task.id)
                    # Play sound
                    st.markdown("""
                        <audio autoplay>
                            <source src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3" type="audio/mpeg">
                        </audio>
                    """, unsafe_allow_html=True)
        except ValueError:
            pass
            
    db.close()

# Show reminder notification (will only display during 11 AM - 12 PM)
show_daily_reminder()
check_task_reminders()

# --- Premium Custom Styling ---
st.markdown("""
    <style>
    /* Import Google Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Root variables for consistent theming */
    :root {
        --bg-primary: #0a0a0f;
        --bg-secondary: rgba(20, 20, 35, 0.8);
        --accent-cyan: #00d4ff;
        --accent-purple: #a855f7;
        --accent-pink: #ec4899;
        --accent-green: #10b981;
        --glass-bg: rgba(255, 255, 255, 0.05);
        --glass-border: rgba(255, 255, 255, 0.1);
        --text-primary: #ffffff;
        --text-secondary: rgba(255, 255, 255, 0.7);
    }
    
    /* Main app background with animated gradient */
    .stApp {
        background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 25%, #16213e 50%, #0f3460 75%, #0a0a0f 100%);
        background-size: 400% 400%;
        animation: gradientShift 15s ease infinite;
    }
    
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    /* Global font */
    /* Global font - target specific containers instead of * to avoid breaking icons */
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(10, 10, 20, 0.95) 0%, rgba(20, 20, 40, 0.95) 100%);
        backdrop-filter: blur(20px);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    [data-testid="stSidebar"] .stRadio > label {
        color: white !important;
        font-weight: 500;
    }
    
    /* Glowing buttons */
    .stButton > button {
        width: 100%;
        border-radius: 12px;
        height: 3em;
        background: linear-gradient(135deg, rgba(168, 85, 247, 0.2) 0%, rgba(0, 212, 255, 0.2) 100%);
        color: #00d4ff;
        border: 1px solid rgba(0, 212, 255, 0.5);
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        transition: all 0.3s ease;
        box-shadow: 0 0 20px rgba(0, 212, 255, 0.1);
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, rgba(0, 212, 255, 0.4) 0%, rgba(168, 85, 247, 0.4) 100%);
        border-color: #00d4ff;
        box-shadow: 0 0 30px rgba(0, 212, 255, 0.4), 0 0 60px rgba(168, 85, 247, 0.2);
        transform: translateY(-2px);
    }
    
    /* Glassmorphism cards */
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 24px;
        margin-bottom: 16px;
        transition: all 0.3s ease;
    }
    
    .glass-card:hover {
        border-color: rgba(0, 212, 255, 0.3);
        box-shadow: 0 8px 32px rgba(0, 212, 255, 0.1);
        transform: translateY(-4px);
    }
    
    /* KPI Cards */
    .kpi-card {
        background: linear-gradient(135deg, rgba(168, 85, 247, 0.1) 0%, rgba(0, 212, 255, 0.1) 100%);
        backdrop-filter: blur(20px);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 24px;
        text-align: center;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .kpi-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, #a855f7, #00d4ff, #ec4899);
        background-size: 200% 100%;
        animation: shimmer 2s infinite;
    }
    
    @keyframes shimmer {
        0% { background-position: -200% 0; }
        100% { background-position: 200% 0; }
    }
    
    .kpi-card:hover {
        transform: translateY(-8px) scale(1.02);
        box-shadow: 0 20px 40px rgba(0, 212, 255, 0.2);
    }
    
    .kpi-value {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #00d4ff, #a855f7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .kpi-label {
        color: rgba(255, 255, 255, 0.7);
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 8px;
    }
    
    /* Task Cards */
    .task-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 20px;
        margin-bottom: 12px;
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        gap: 16px;
    }
    
    .task-card:hover {
        background: rgba(255, 255, 255, 0.06);
        border-color: rgba(0, 212, 255, 0.3);
        transform: translateX(8px);
    }
    
    .task-priority-high {
        border-left: 4px solid #ef4444;
    }
    
    .task-priority-medium {
        border-left: 4px solid #f59e0b;
    }
    
    .task-priority-low {
        border-left: 4px solid #10b981;
    }
    
    .task-title {
        font-weight: 600;
        font-size: 1.1rem;
        color: #fff;
        margin-bottom: 4px;
    }
    
    .task-desc {
        color: rgba(255, 255, 255, 0.6);
        font-size: 0.9rem;
    }
    
    /* Badge Cards */
    .badge-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(20px);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 30px 20px;
        text-align: center;
        transition: all 0.4s ease;
        position: relative;
        overflow: hidden;
    }
    
    .badge-card.unlocked {
        background: linear-gradient(135deg, rgba(168, 85, 247, 0.15) 0%, rgba(0, 212, 255, 0.15) 100%);
    }
    
    .badge-card.unlocked::after {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: linear-gradient(45deg, transparent, rgba(255,255,255,0.1), transparent);
        animation: shine 3s infinite;
    }
    
    @keyframes shine {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    .badge-card:hover {
        transform: scale(1.05);
        box-shadow: 0 10px 40px rgba(168, 85, 247, 0.3);
    }
    
    .badge-icon {
        font-size: 48px;
        margin-bottom: 16px;
        display: block;
    }
    
    .badge-locked {
        filter: grayscale(1) blur(1px);
        opacity: 0.4;
    }
    
    /* Form inputs */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        color: white !important;
        transition: all 0.3s ease !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: rgba(0, 212, 255, 0.5) !important;
        box-shadow: 0 0 20px rgba(0, 212, 255, 0.2) !important;
    }
    
    /* Selectbox and sliders */
    .stSlider > div > div > div {
        background: linear-gradient(90deg, #a855f7, #00d4ff) !important;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: rgba(255, 255, 255, 0.05) !important;
        border-radius: 12px !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    
    /* Metric styling */
    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 700 !important;
        background: linear-gradient(135deg, #00d4ff, #a855f7) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
    }
    
    [data-testid="stMetricLabel"] {
        color: rgba(255, 255, 255, 0.7) !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        font-size: 0.8rem !important;
    }
    
    /* Info boxes */
    .stAlert {
        background: rgba(0, 212, 255, 0.1) !important;
        border: 1px solid rgba(0, 212, 255, 0.3) !important;
        border-radius: 12px !important;
    }
    
    /* Success message */
    .stSuccess {
        background: rgba(16, 185, 129, 0.1) !important;
        border: 1px solid rgba(16, 185, 129, 0.3) !important;
        border-radius: 12px !important;
    }
    
    /* Plotly chart background */
    .js-plotly-plot {
        border-radius: 16px !important;
        overflow: hidden !important;
    }
    
    /* Page titles */
    h1 {
        background: linear-gradient(135deg, #ffffff 0%, #00d4ff 50%, #a855f7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-weight: 700 !important;
        letter-spacing: -1px;
    }
    
    h2, h3 {
        color: rgba(255, 255, 255, 0.9) !important;
        font-weight: 600 !important;
    }
    
    /* Scrollbar styling */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.05);
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, #a855f7, #00d4ff);
        border-radius: 4px;
    }
    
    /* Pulse animation for active elements */
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    
    .pulse {
        animation: pulse 2s infinite;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Sidebar Navigation ---
# --- Sidebar Navigation ---
st.sidebar.markdown(f"""
    <div style="text-align: center; padding: 20px 0;">
        <h1 style="font-size: 1.8rem; margin: 0;">🚀</h1>
        <h2 style="font-size: 1.2rem; margin: 10px 0; background: linear-gradient(90deg, #00d4ff, #a855f7); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Productivity AI</h2>
        <p style="color: rgba(255,255,255,0.5); font-size: 0.85rem; margin: 0;">👤 {st.session_state.get('username', 'User')}</p>
    </div>
""", unsafe_allow_html=True)

# Logout button
if st.sidebar.button("🚪 Logout", use_container_width=True):
    for key in ['user_id', 'username', 'navigation', 'goal_agent']:
        st.session_state.pop(key, None)
    st.rerun()

st.sidebar.markdown("---")

# Navigation Logic
if 'navigation' not in st.session_state:
    st.session_state.navigation = "Dashboard"

if 'nav_to' in st.session_state:
    st.session_state.navigation = st.session_state.pop('nav_to')

menu = st.sidebar.radio("Navigation", ["Dashboard", "My Tasks", "📅 Day Planner", "AI Goal Planner", "Achievements"], key="navigation")

# Add sidebar footer
st.sidebar.markdown("""
    <div style="position: fixed; bottom: 20px; left: 20px; right: 20px; text-align: center;">
        <p style="color: rgba(255,255,255,0.4); font-size: 0.75rem;">Built with ❤️ & AI</p>
    </div>
""", unsafe_allow_html=True)

# Persistent Agents
if 'goal_agent' not in st.session_state:
    st.session_state.goal_agent = GoalAgent()

# --- Dashboard ---
if menu == "Dashboard":
    # Get data first
    dates, scores, counts = get_productivity_trends()
    db = SessionLocal()
    streak = db.query(UserStats).order_by(UserStats.date.desc()).first()
    streak_val = streak.streak_count if streak else 0
    total_tasks_completed = db.query(Task).filter(Task.status == "Completed", Task.user_id == current_user_id).count()
    pending_tasks = db.query(Task).filter(Task.status != "Completed", Task.user_id == current_user_id).count()
    today_tasks = db.query(Task).filter(Task.due_date == date.today(), Task.status != "Completed", Task.user_id == current_user_id).all()
    forecast = forecast_productivity()
    
    # Time-based greeting
    current_hour = datetime.now().hour
    if current_hour < 12:
        greeting = "Good Morning"
        greeting_emoji = "🌅"
    elif current_hour < 17:
        greeting = "Good Afternoon"
        greeting_emoji = "☀️"
    else:
        greeting = "Good Evening"
        greeting_emoji = "🌙"
    
    # Motivational quotes
    import random
    quotes = [
        ("The secret of getting ahead is getting started.", "Mark Twain"),
        ("Focus on being productive instead of busy.", "Tim Ferriss"),
        ("Small progress is still progress.", "Unknown"),
        ("Your future is created by what you do today.", "Robert Kiyosaki"),
        ("Done is better than perfect.", "Sheryl Sandberg"),
        ("The only way to do great work is to love what you do.", "Steve Jobs"),
    ]
    quote, author = random.choice(quotes)
    
    # Hero Section with Greeting
    st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, rgba(168, 85, 247, 0.2) 0%, rgba(0, 212, 255, 0.2) 100%);
            border-radius: 24px;
            padding: 40px;
            margin-bottom: 30px;
            border: 1px solid rgba(255,255,255,0.1);
            position: relative;
            overflow: hidden;
        ">
            <div style="position: absolute; top: -50px; right: -50px; font-size: 150px; opacity: 0.1;">{greeting_emoji}</div>
            <h1 style="font-size: 2.5rem; margin: 0 0 10px 0; background: linear-gradient(90deg, #fff, #00d4ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{greeting}! 👋</h1>
            <p style="color: rgba(255,255,255,0.7); font-size: 1.2rem; margin: 0 0 20px 0;">Ready to crush your goals today?</p>
            <div style="
                background: rgba(0,0,0,0.2);
                border-radius: 12px;
                padding: 15px 20px;
                display: inline-block;
                border-left: 3px solid #00d4ff;
            ">
                <p style="color: rgba(255,255,255,0.9); font-style: italic; margin: 0;">"{quote}"</p>
                <p style="color: rgba(255,255,255,0.5); font-size: 0.85rem; margin: 5px 0 0 0;">— {author}</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # --- Thought of the Day ---
    import calendar as cal_mod
    thoughts = [
        "Believe you can and you're halfway there.",
        "Success is the sum of small efforts, repeated day in and day out.",
        "Start where you are. Use what you have. Do what you can.",
        "Every accomplishment starts with the decision to try.",
        "Don't watch the clock; do what it does. Keep going.",
        "The future depends on what you do today.",
        "Productivity is never an accident. It is always the result of commitment.",
        "Focus on progress, not perfection.",
    ]
    thought_of_day = thoughts[date.today().toordinal() % len(thoughts)]
    
    st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, rgba(0,212,255,0.15) 0%, rgba(168,85,247,0.15) 100%);
            border-radius: 16px; padding: 20px 28px; margin-bottom: 24px;
            border: 1px solid rgba(255,255,255,0.1);
            display: flex; align-items: center; gap: 16px;
        ">
            <div style="font-size: 2.2rem;">💭</div>
            <div>
                <div style="color: rgba(255,255,255,0.5); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px;">Thought of the Day</div>
                <div style="color: #fff; font-size: 1.1rem; font-weight: 500; font-style: italic;">"{thought_of_day}"</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # --- Full Monthly Calendar Grid ---
    today = date.today()
    cal_year, cal_month = today.year, today.month
    month_name = today.strftime("%B %Y")
    first_day_weekday = cal_mod.monthrange(cal_year, cal_month)[0]  # 0=Mon
    days_in_month = cal_mod.monthrange(cal_year, cal_month)[1]

    # Convert Monday=0 start to Sunday=0 start
    start_offset = (first_day_weekday + 1) % 7

    # Get task counts per day for this month
    month_tasks_raw = db.query(Task).filter(
        Task.user_id == current_user_id,
        Task.due_date >= date(cal_year, cal_month, 1),
        Task.due_date <= date(cal_year, cal_month, days_in_month)
    ).all()
    task_count_by_day = {}
    for tk in month_tasks_raw:
        if tk.due_date:
            d = tk.due_date.day
            task_count_by_day[d] = task_count_by_day.get(d, 0) + 1

    day_headers = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    header_html = "".join(
        f'<div style="text-align:center; font-weight:700; color:{("#ef4444" if i in (0,6) else "rgba(255,255,255,0.7)")}; font-size:0.85rem; padding: 10px 0;">{d}</div>'
        for i, d in enumerate(day_headers)
    )

    cells_html = ""
    # Empty cells before month starts
    for _ in range(start_offset):
        cells_html += '<div style="min-height:70px; border: 1px solid rgba(255,255,255,0.05); padding: 6px;"></div>'

    for day in range(1, days_in_month + 1):
        is_today = (day == today.day)
        weekday_idx = (start_offset + day - 1) % 7
        is_weekend = weekday_idx in (0, 6)
        tc = task_count_by_day.get(day, 0)

        bg = "rgba(0,212,255,0.2)" if is_today else ("rgba(239,68,68,0.06)" if is_weekend else "rgba(255,255,255,0.02)")
        border = "2px solid #00d4ff" if is_today else "1px solid rgba(255,255,255,0.06)"
        num_color = "#00d4ff" if is_today else ("#ef4444" if is_weekend else "rgba(255,255,255,0.8)")
        dot_html = f'<div style="margin-top:4px;"><span style="background:#a855f7; color:#fff; font-size:0.65rem; padding:1px 6px; border-radius:8px;">{tc} task{"s" if tc != 1 else ""}</span></div>' if tc > 0 else ""

        cells_html += f'''<div style="min-height:70px; border:{border}; padding:6px; background:{bg}; border-radius:4px; transition: all 0.2s ease;">
            <div style="font-weight:{'700' if is_today else '500'}; font-size:0.95rem; color:{num_color};">{day}</div>
            {dot_html}
        </div>'''

    # Fill remaining cells to complete the grid
    total_cells = start_offset + days_in_month
    remaining = (7 - total_cells % 7) % 7
    for _ in range(remaining):
        cells_html += '<div style="min-height:70px; border: 1px solid rgba(255,255,255,0.05); padding: 6px;"></div>'

    st.markdown(f"""
        <div class="glass-card" style="padding: 24px; margin-bottom: 24px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                <h3 style="margin: 0; background: linear-gradient(90deg, #fff, #00d4ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">📅 {month_name}</h3>
                <div style="color: rgba(255,255,255,0.5); font-size: 0.85rem;">Today: {today.strftime('%A, %b %d')}</div>
            </div>
            <div style="display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px;">
                {header_html}
                {cells_html}
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Main Dashboard Layout - Two Columns
    left_col, right_col = st.columns([2, 1])
    
    with left_col:
        # KPI Cards Row
        st.markdown("<h3 style='margin-bottom: 20px;'>📊 Today's Overview</h3>", unsafe_allow_html=True)
        
        k1, k2, k3, k4 = st.columns(4)
        
        with k1:
            score_val = scores[-1] if scores else 0
            # Circular progress indicator
            st.markdown(f"""
                <div class="kpi-card" style="position: relative;">
                    <svg viewBox="0 0 100 100" style="width: 80px; height: 80px; margin: 0 auto 10px;">
                        <circle cx="50" cy="50" r="40" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="8"/>
                        <circle cx="50" cy="50" r="40" fill="none" stroke="url(#gradient1)" stroke-width="8" 
                            stroke-dasharray="{score_val * 2.51} 251" stroke-linecap="round"
                            transform="rotate(-90 50 50)" style="transition: all 1s ease;"/>
                        <defs><linearGradient id="gradient1" x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" style="stop-color:#a855f7"/>
                            <stop offset="100%" style="stop-color:#00d4ff"/>
                        </linearGradient></defs>
                        <text x="50" y="55" text-anchor="middle" fill="#fff" font-size="18" font-weight="bold">{score_val:.0f}</text>
                    </svg>
                    <div class="kpi-label">Score</div>
                </div>
            """, unsafe_allow_html=True)
        
        with k2:
            tasks_today = counts[-1] if counts else 0
            st.markdown(f"""
                <div class="kpi-card">
                    <div style="font-size: 3rem; margin-bottom: 5px;">✅</div>
                    <div class="kpi-value" style="font-size: 2rem;">{tasks_today}</div>
                    <div class="kpi-label">Done Today</div>
                </div>
            """, unsafe_allow_html=True)
        
        with k3:
            st.markdown(f"""
                <div class="kpi-card">
                    <div style="font-size: 3rem; margin-bottom: 5px;">🔥</div>
                    <div class="kpi-value" style="font-size: 2rem;">{streak_val}</div>
                    <div class="kpi-label">Day Streak</div>
                </div>
            """, unsafe_allow_html=True)
        
        with k4:
            forecast_val = f"{forecast:.0f}" if forecast else "—"
            st.markdown(f"""
                <div class="kpi-card">
                    <div style="font-size: 3rem; margin-bottom: 5px;">🎯</div>
                    <div class="kpi-value" style="font-size: 2rem;">{forecast_val}</div>
                    <div class="kpi-label">Forecast</div>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Multiple Chart Types with Tabs
        if dates:
            df = pd.DataFrame({"Date": dates, "Score": scores, "Tasks": counts})
            
            st.markdown("""
                <div class="glass-card" style="padding: 20px;">
                    <h4 style="margin: 0 0 15px 0; color: #fff;">📊 Analytics Dashboard</h4>
            """, unsafe_allow_html=True)
            
            # Chart type selector using tabs
            chart_tab1, chart_tab2, chart_tab3, chart_tab4 = st.tabs([
                "📈 Line Chart", 
                "📊 Bar Chart", 
                "📉 Area Chart", 
                "🔄 Combined View"
            ])
            
            with chart_tab1:
                # Line Chart - Productivity Score over time
                fig_line = go.Figure()
                fig_line.add_trace(go.Scatter(
                    x=df["Date"], y=df["Score"],
                    mode='lines+markers',
                    line=dict(color='#00d4ff', width=3, shape='spline'),
                    marker=dict(size=10, color='#a855f7', line=dict(width=2, color='#00d4ff')),
                    name='Productivity Score',
                    hovertemplate='<b>Date:</b> %{x}<br><b>Score:</b> %{y:.1f}<extra></extra>'
                ))
                fig_line.update_layout(
                    template="plotly_dark",
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(gridcolor='rgba(255,255,255,0.05)', title=None),
                    yaxis=dict(gridcolor='rgba(255,255,255,0.05)', title="Score"),
                    font=dict(color='rgba(255,255,255,0.7)'),
                    margin=dict(l=40, r=20, t=20, b=40),
                    showlegend=False,
                    height=300
                )
                st.plotly_chart(fig_line, use_container_width=True)
                st.caption("📈 Shows your productivity score trend over time")
            
            with chart_tab2:
                # Bar Chart - Tasks completed per day
                fig_bar = go.Figure()
                fig_bar.add_trace(go.Bar(
                    x=df["Date"], y=df["Tasks"],
                    marker=dict(
                        color=df["Tasks"],
                        colorscale=[[0, '#a855f7'], [0.5, '#00d4ff'], [1, '#10b981']],
                        line=dict(width=0)
                    ),
                    name='Tasks Completed',
                    hovertemplate='<b>Date:</b> %{x}<br><b>Tasks:</b> %{y}<extra></extra>'
                ))
                fig_bar.update_layout(
                    template="plotly_dark",
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(gridcolor='rgba(255,255,255,0.05)', title=None),
                    yaxis=dict(gridcolor='rgba(255,255,255,0.05)', title="Tasks"),
                    font=dict(color='rgba(255,255,255,0.7)'),
                    margin=dict(l=40, r=20, t=20, b=40),
                    showlegend=False,
                    height=300,
                    bargap=0.3
                )
                st.plotly_chart(fig_bar, use_container_width=True)
                st.caption("📊 Shows the number of tasks completed each day")
            
            with chart_tab3:
                # Area Chart - Score with gradient fill
                fig_area = go.Figure()
                fig_area.add_trace(go.Scatter(
                    x=df["Date"], y=df["Score"],
                    fill='tozeroy',
                    fillcolor='rgba(0, 212, 255, 0.2)',
                    line=dict(color='#00d4ff', width=2),
                    mode='lines',
                    name='Productivity Score',
                    hovertemplate='<b>Date:</b> %{x}<br><b>Score:</b> %{y:.1f}<extra></extra>'
                ))
                # Add a second area for tasks (scaled)
                max_score = max(scores) if scores else 100
                max_tasks = max(1, max(counts)) if counts else 1  # Avoid division by zero
                scale_factor = (max_score / max_tasks) * 0.8 if max_tasks > 0 else 0
                scaled_tasks = [t * scale_factor for t in counts]
                fig_area.add_trace(go.Scatter(
                    x=df["Date"], y=scaled_tasks,
                    fill='tozeroy',
                    fillcolor='rgba(168, 85, 247, 0.2)',
                    line=dict(color='#a855f7', width=2),
                    mode='lines',
                    name='Tasks (scaled)',
                    hovertemplate='<b>Date:</b> %{x}<br><b>Tasks:</b> %{y:.0f}<extra></extra>'
                ))
                fig_area.update_layout(
                    template="plotly_dark",
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(gridcolor='rgba(255,255,255,0.05)', title=None),
                    yaxis=dict(gridcolor='rgba(255,255,255,0.05)', title="Value"),
                    font=dict(color='rgba(255,255,255,0.7)'),
                    margin=dict(l=40, r=20, t=20, b=40),
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    height=300
                )
                st.plotly_chart(fig_area, use_container_width=True)
                st.caption("📉 Area visualization showing score and tasks trends")
            
            with chart_tab4:
                # Combined Chart - Dual axis showing both metrics
                fig_combined = go.Figure()
                
                # Productivity Score (primary y-axis)
                fig_combined.add_trace(go.Scatter(
                    x=df["Date"], y=df["Score"],
                    mode='lines+markers',
                    line=dict(color='#00d4ff', width=3),
                    marker=dict(size=8, color='#00d4ff'),
                    name='Score',
                    yaxis='y',
                    hovertemplate='<b>Score:</b> %{y:.1f}<extra></extra>'
                ))
                
                # Tasks Completed (secondary y-axis as bars)
                fig_combined.add_trace(go.Bar(
                    x=df["Date"], y=df["Tasks"],
                    marker=dict(color='rgba(168, 85, 247, 0.6)'),
                    name='Tasks',
                    yaxis='y2',
                    hovertemplate='<b>Tasks:</b> %{y}<extra></extra>'
                ))
                
                fig_combined.update_layout(
                    template="plotly_dark",
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(gridcolor='rgba(255,255,255,0.05)', title=None),
                    yaxis=dict(
                        gridcolor='rgba(255,255,255,0.05)', 
                        title=dict(text="Score", font=dict(color='#00d4ff')),
                        tickfont=dict(color='#00d4ff'),
                        side='left'
                    ),
                    yaxis2=dict(
                        title=dict(text="Tasks", font=dict(color='#a855f7')),
                        tickfont=dict(color='#a855f7'),
                        overlaying='y',
                        side='right',
                        gridcolor='rgba(255,255,255,0.02)'
                    ),
                    font=dict(color='rgba(255,255,255,0.7)'),
                    margin=dict(l=50, r=50, t=20, b=40),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
                    height=300,
                    bargap=0.4
                )
                st.plotly_chart(fig_combined, use_container_width=True)
                st.caption("🔄 Combined view showing score trend with task bars")
            
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown("""
                <div class="glass-card" style="text-align: center; padding: 60px 40px;">
                    <div style="font-size: 4rem; margin-bottom: 20px; opacity: 0.5;">📈</div>
                    <h4 style="color: rgba(255,255,255,0.7); margin: 0;">No data yet</h4>
                    <p style="color: rgba(255,255,255,0.4); margin: 10px 0 0 0;">Complete some tasks to see your productivity trends!</p>
                </div>
            """, unsafe_allow_html=True)
    
    with right_col:
        # Quick Actions
        st.markdown("<h3 style='margin-bottom: 20px;'>⚡ Quick Actions</h3>", unsafe_allow_html=True)
        
        # Removed wrapping div to fix clickability issues
        if st.button("➕ Add New Task", key="quick_add_task", use_container_width=True):
            st.session_state['nav_to'] = "My Tasks"
            st.rerun()
        
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        
        if st.button("🎯 Create New Goal", key="quick_add_goal", use_container_width=True):
            st.session_state['nav_to'] = "AI Goal Planner"
            st.rerun()
        
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        
        if st.button("🏆 View Achievements", key="quick_achievements", use_container_width=True):
            st.session_state['nav_to'] = "Achievements"
            st.rerun()
        
        # Today's Focus Panel
        st.markdown("<h3 style='margin-top: 30px; margin-bottom: 20px;'>🎯 Today's Focus</h3>", unsafe_allow_html=True)
        
        if today_tasks:
            for i, task in enumerate(today_tasks[:5]):  # Show max 5
                priority_color = "#ef4444" if task.priority == 3 else "#f59e0b" if task.priority == 2 else "#10b981"
                st.markdown(f"""
                    <div style="
                        background: rgba(255,255,255,0.03);
                        border-radius: 12px;
                        padding: 15px;
                        margin-bottom: 10px;
                        border-left: 3px solid {priority_color};
                        transition: all 0.3s ease;
                    ">
                        <div style="font-weight: 600; color: #fff; font-size: 0.95rem;">{task.title}</div>
                        <div style="color: rgba(255,255,255,0.5); font-size: 0.8rem; margin-top: 4px;">
                            {"🔴 High" if task.priority == 3 else "🟡 Medium" if task.priority == 2 else "🟢 Low"} priority
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            
            if len(today_tasks) > 5:
                st.markdown(f"""
                    <p style="text-align: center; color: rgba(255,255,255,0.4); font-size: 0.85rem;">
                        +{len(today_tasks) - 5} more tasks
                    </p>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
                <div class="glass-card" style="text-align: center; padding: 30px;">
                    <div style="font-size: 2.5rem; margin-bottom: 10px;">🎉</div>
                    <p style="color: rgba(255,255,255,0.5); margin: 0;">All caught up!</p>
                    <p style="color: rgba(255,255,255,0.3); font-size: 0.85rem; margin-top: 5px;">Add new tasks to stay productive</p>
                </div>
            """, unsafe_allow_html=True)
        
        # Weekly Summary
        st.markdown("<h3 style='margin-top: 30px; margin-bottom: 20px;'>📅 This Week</h3>", unsafe_allow_html=True)
        
        weekly_completed = sum(counts[-7:]) if len(counts) >= 7 else sum(counts)
        weekly_avg = sum(scores[-7:]) / min(len(scores), 7) if scores else 0
        
        st.markdown(f"""
            <div class="glass-card" style="padding: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <div>
                        <div style="color: rgba(255,255,255,0.5); font-size: 0.8rem; text-transform: uppercase;">Tasks Done</div>
                        <div style="font-size: 1.8rem; font-weight: bold; color: #00d4ff;">{weekly_completed}</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="color: rgba(255,255,255,0.5); font-size: 0.8rem; text-transform: uppercase;">Avg Score</div>
                        <div style="font-size: 1.8rem; font-weight: bold; color: #a855f7;">{weekly_avg:.0f}</div>
                    </div>
                </div>
                <div style="height: 6px; background: rgba(255,255,255,0.1); border-radius: 3px; overflow: hidden;">
                    <div style="width: {min(weekly_avg, 100)}%; height: 100%; background: linear-gradient(90deg, #a855f7, #00d4ff); border-radius: 3px;"></div>
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    db.close()

# --- My Tasks ---
elif menu == "My Tasks":
    st.title("📋 Task Management")
    st.markdown("<p style='color: rgba(255,255,255,0.6); margin-top: -10px;'>Manage and complete your daily tasks</p>", unsafe_allow_html=True)
    
    db = SessionLocal()
    
    # Task Entry
    with st.expander("➕ Add New Task", expanded=False):
        with st.form("new_task"):
            title = st.text_input("Task Title", placeholder="What do you need to do?")
            desc = st.text_area("Description", placeholder="Add some details...")
            col1, col2, col3 = st.columns(3)
            with col1:
                priority = st.select_slider("Priority", options=["Low", "Medium", "High"], value="Medium")
            with col2:
                difficulty = st.slider("Difficulty", 1, 5, 3)
            with col3:
                category = st.selectbox("Category", ["General", "Learning", "Coding", "Health", "Work", "Personal"])
            col4, col5 = st.columns(2)
            with col4:
                due_date = st.date_input("📅 Due Date", value=date.today())
            with col5:
                reminder_time = st.time_input("⏰ Reminder Time (optional)", value=None)
            submitted = st.form_submit_button("✨ Add Task")
            if submitted and title:
                priority_map = {"Low": 1, "Medium": 2, "High": 3}
                rem_str = None
                if reminder_time:
                    rem_dt = datetime.combine(due_date, reminder_time)
                    rem_str = rem_dt.isoformat()
                new_t = Task(title=title, description=desc, priority=priority_map[priority], difficulty=difficulty, category=category, due_date=due_date, reminder_time=rem_str, user_id=current_user_id)
                db.add(new_t)
                db.commit()
                st.success("🎉 Task added successfully!")
                st.rerun()

    # List Tasks
    st.markdown("<h3 style='margin-top: 20px;'>📌 Pending Tasks</h3>", unsafe_allow_html=True)
    tasks = db.query(Task).filter(Task.status != "Completed", Task.user_id == current_user_id).all()
    
    if tasks:
        for t in tasks:
            priority_class = "high" if t.priority == 3 else "medium" if t.priority == 2 else "low"
            priority_emoji = "🔴" if t.priority == 3 else "🟡" if t.priority == 2 else "🟢"
            
            col1, col2, col3 = st.columns([0.65, 0.2, 0.15])
            with col1:
                st.markdown(f"""
                    <div class="task-card task-priority-{priority_class}">
                        <div>
                            <div class="task-title">{priority_emoji} {t.title} <span style="font-size: 0.7rem; background: rgba(255,255,255,0.1); padding: 2px 6px; border-radius: 4px; margin-left: 8px; color: rgba(255,255,255,0.7);">{t.category}</span></div>
                            <div class="task-desc">{t.description if t.description else 'No description'}</div>
                            <div style="font-size: 0.75rem; color: rgba(255,255,255,0.4); margin-top: 5px;">
                                ⏱️ Spent: {t.time_spent // 60}m {t.time_spent % 60}s | 📅 Due: {t.due_date} {f"| ⏰ {datetime.fromisoformat(t.reminder_time).strftime('%H:%M')}" if t.reminder_time else ""}
                            </div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                # Inline Edit Form
                if st.session_state.get(f'edit_mode_{t.id}', False):
                    with st.expander("✏️ Edit Task", expanded=True):
                        with st.form(f"edit_task_{t.id}"):
                            new_title = st.text_input("Title", value=t.title)
                            new_desc = st.text_area("Description", value=t.description)
                            c1, c2, c3 = st.columns(3)
                            with c1:
                                new_priority = st.selectbox("Priority", ["Low", "Medium", "High"], index=["Low", "Medium", "High"].index(["Low", "Medium", "High"][t.priority-1]))
                            with c2:
                                reminder_val = None
                                if t.reminder_time:
                                    try:
                                        reminder_val = datetime.fromisoformat(t.reminder_time).time()
                                    except:
                                        pass
                                new_reminder = st.time_input("Set Reminder", value=reminder_val)
                            with c3:
                                new_due_date = st.date_input("Due Date", value=t.due_date)
                                
                            if st.form_submit_button("💾 Save Changes"):
                                t.title = new_title
                                t.description = new_desc
                                t.priority = {"Low": 1, "Medium": 2, "High": 3}[new_priority]
                                t.due_date = new_due_date
                                if new_reminder:
                                    # Combine today/due date with time for reminder
                                    rem_dt = datetime.combine(date.today(), new_reminder)
                                    # If time is in past for today, assume it's for the due date
                                    if rem_dt < datetime.now() and new_due_date > date.today():
                                        rem_dt = datetime.combine(new_due_date, new_reminder)
                                    t.reminder_time = rem_dt.isoformat()
                                else:
                                    t.reminder_time = None
                                    
                                db.commit()
                                st.session_state[f'edit_mode_{t.id}'] = False
                                st.success("Task updated!")
                                st.rerun()

            with col2:
                # Timer Controls
                if st.session_state.get('active_timer_task_id') == t.id:
                    # Active Timer
                    elapsed = int((datetime.now() - st.session_state['active_timer_start']).total_seconds())
                    st.info(f"⏱️ {elapsed // 60}:{elapsed % 60:02d}")
                    if st.button("⏹ Stop", key=f"stop_timer_{t.id}"):
                        t.time_spent += elapsed
                        db.commit()
                        st.session_state['active_timer_task_id'] = None
                        st.rerun()
                else:
                    # Inactive Timer
                    if st.button("▶ Start", key=f"start_timer_{t.id}"):
                        st.session_state['active_timer_task_id'] = t.id
                        st.session_state['active_timer_start'] = datetime.now()
                        st.rerun()
                        
            with col3:
                if st.button("✏️ Edit", key=f"edit_btn_{t.id}"):
                    st.session_state[f'edit_mode_{t.id}'] = not st.session_state.get(f'edit_mode_{t.id}', False)
                    st.rerun()
                    
                if st.button("✅ Done", key=f"done_{t.id}"):
                    t.status = "Completed"
                    db.commit()
                    update_daily_stats()
                    st.balloons()
                    st.rerun()

                if st.button("❌ Delete", key=f"del_{t.id}"):
                    db.delete(t)
                    db.commit()
                    st.rerun()
    else:
        st.markdown("""
            <div class="glass-card" style="text-align: center; padding: 40px;">
                <p style="font-size: 1.2rem; color: rgba(255,255,255,0.5);">🎉 All caught up! No pending tasks.</p>
            </div>
        """, unsafe_allow_html=True)
    
    # Completed Tasks
    st.markdown("<h3 style='margin-top: 30px;'>✅ Completed</h3>", unsafe_allow_html=True)
    done_tasks = db.query(Task).filter(Task.status == "Completed", Task.user_id == current_user_id).order_by(Task.id.desc()).limit(5).all()
    
    if done_tasks:
        for t in done_tasks:
            st.markdown(f"""
                <div style="padding: 12px 20px; background: rgba(16, 185, 129, 0.1); border-radius: 10px; margin-bottom: 8px; border-left: 3px solid #10b981;">
                    <span style="text-decoration: line-through; color: rgba(255,255,255,0.5);">{t.title}</span>
                    <span style="float: right; color: #10b981;">✓</span>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("<p style='color: rgba(255,255,255,0.4);'>No completed tasks yet. Get started!</p>", unsafe_allow_html=True)
        
    db.close()

# --- Day Planner with Calendar ---
elif menu == "📅 Day Planner":
    st.title("📅 Day Planner")
    st.markdown("<p style='color: rgba(255,255,255,0.6); margin-top: -10px;'>Plan your day, tick off completed tasks, and stay organized</p>", unsafe_allow_html=True)

    db = SessionLocal()

    # Calendar date picker
    left_col, right_col = st.columns([1, 2])
    with left_col:
        st.markdown("<h3>📆 Select Date</h3>", unsafe_allow_html=True)
        selected_date = st.date_input("Pick a date", value=date.today(), key="planner_date", label_visibility="collapsed")

        # Mini stats for selected date
        day_tasks = db.query(Task).filter(Task.due_date == selected_date, Task.user_id == current_user_id).all()
        done_count = sum(1 for t in day_tasks if t.status == "Completed")
        pending_count = sum(1 for t in day_tasks if t.status != "Completed")

        st.markdown(f"""
            <div class="glass-card" style="padding: 16px; text-align: center;">
                <div style="display: flex; justify-content: space-around;">
                    <div><div style="font-size: 1.5rem; font-weight: bold; color: #00d4ff;">{len(day_tasks)}</div><div style="color: rgba(255,255,255,0.5); font-size: 0.8rem;">Total</div></div>
                    <div><div style="font-size: 1.5rem; font-weight: bold; color: #10b981;">{done_count}</div><div style="color: rgba(255,255,255,0.5); font-size: 0.8rem;">Done</div></div>
                    <div><div style="font-size: 1.5rem; font-weight: bold; color: #f59e0b;">{pending_count}</div><div style="color: rgba(255,255,255,0.5); font-size: 0.8rem;">Pending</div></div>
                </div>
                <div style="margin-top: 12px; background: rgba(255,255,255,0.1); border-radius: 6px; height: 6px; overflow: hidden;">
                    <div style="width: {(done_count / max(len(day_tasks), 1)) * 100}%; height: 100%; background: linear-gradient(90deg, #10b981, #00d4ff); border-radius: 6px;"></div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Quick add task
        st.markdown("<h4 style='margin-top: 20px;'>➕ Quick Add</h4>", unsafe_allow_html=True)
        with st.form("quick_add_planner"):
            q_title = st.text_input("Task", placeholder="What needs to be done?", label_visibility="collapsed")
            q_col1, q_col2 = st.columns(2)
            with q_col1:
                q_priority = st.selectbox("Priority", ["Low", "Medium", "High"], index=1, key="qp_pri")
            with q_col2:
                q_reminder = st.time_input("⏰ Reminder", value=None, key="qp_rem")
            if st.form_submit_button("➕ Add", use_container_width=True):
                if q_title:
                    rem_str = None
                    if q_reminder:
                        rem_str = datetime.combine(selected_date, q_reminder).isoformat()
                    new_t = Task(title=q_title, due_date=selected_date, priority={"Low": 1, "Medium": 2, "High": 3}[q_priority], user_id=current_user_id, reminder_time=rem_str)
                    db.add(new_t)
                    db.commit()
                    st.rerun()

    with right_col:
        st.markdown(f"<h3>📋 Tasks for {selected_date.strftime('%A, %b %d, %Y')}</h3>", unsafe_allow_html=True)

        pending_tasks = [t for t in day_tasks if t.status != "Completed"]
        completed_tasks = [t for t in day_tasks if t.status == "Completed"]

        if pending_tasks:
            for t in pending_tasks:
                p_emoji = "🔴" if t.priority == 3 else "🟡" if t.priority == 2 else "🟢"
                p_color = "#ef4444" if t.priority == 3 else "#f59e0b" if t.priority == 2 else "#10b981"
                rem_text = f" | ⏰ {datetime.fromisoformat(t.reminder_time).strftime('%I:%M %p')}" if t.reminder_time else ""

                tc1, tc2, tc3 = st.columns([0.7, 0.15, 0.15])
                with tc1:
                    st.markdown(f"""
                        <div style="background: rgba(255,255,255,0.03); border-radius: 12px; padding: 14px 18px; border-left: 3px solid {p_color}; margin-bottom: 4px;">
                            <div style="font-weight: 600; color: #fff;">{p_emoji} {t.title}</div>
                            <div style="font-size: 0.75rem; color: rgba(255,255,255,0.4); margin-top: 4px;">
                                {t.category or "General"}{rem_text}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                with tc2:
                    if st.button("✅", key=f"plan_done_{t.id}", help="Mark as complete"):
                        t.status = "Completed"
                        db.commit()
                        update_daily_stats()
                        st.rerun()
                with tc3:
                    if st.button("❌", key=f"plan_del_{t.id}", help="Delete task"):
                        db.delete(t)
                        db.commit()
                        st.rerun()
        else:
            st.markdown("""
                <div class="glass-card" style="text-align: center; padding: 30px;">
                    <div style="font-size: 2rem; margin-bottom: 10px;">🎉</div>
                    <p style="color: rgba(255,255,255,0.5); margin:0;">No pending tasks for this day!</p>
                </div>
            """, unsafe_allow_html=True)

        if completed_tasks:
            st.markdown("<h4 style='margin-top: 20px;'>✅ Completed</h4>", unsafe_allow_html=True)
            for t in completed_tasks:
                st.markdown(f"""
                    <div style="padding: 10px 18px; background: rgba(16,185,129,0.1); border-radius: 10px; margin-bottom: 6px; border-left: 3px solid #10b981;">
                        <span style="text-decoration: line-through; color: rgba(255,255,255,0.5);">{t.title}</span>
                        <span style="float: right; color: #10b981;">✓</span>
                    </div>
                """, unsafe_allow_html=True)

    db.close()

# --- AI Goal Planner ---
elif menu == "AI Goal Planner":
    st.title("🤖 AI Goal Planner")
    st.markdown("<p style='color: rgba(255,255,255,0.6); margin-top: -10px;'>Let AI break down your big goals into actionable steps</p>", unsafe_allow_html=True)
    
    st.markdown("""
        <div class="glass-card" style="border-left: 4px solid #00d4ff;">
            <p style="margin: 0; color: rgba(255,255,255,0.8);">💡 <strong>Pro tip:</strong> Enter a long-term goal, and our AI will create a personalized action plan with daily tasks.</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    with st.form("goal_form"):
        goal_title = st.text_input("🎯 What is your major goal?", placeholder="e.g. Master Machine Learning, Learn Spanish, Build a Startup")
        goal_desc = st.text_area("📝 Provide some context...", placeholder="Tell us more about your goal, your current level, and what you want to achieve...")
        custom_instructions = st.text_area("🔧 Custom Instructions / Project Details", placeholder="Any specific requirements? e.g., 'Focus on practical projects', 'Exclude testing tasks', 'I have 2 hours daily'...")
        target_date = st.date_input("📅 Target Date", value=date.today() + timedelta(days=30))
        plan_it = st.form_submit_button("⚡ Break it Down")
        
        if plan_it and goal_title:
            with st.spinner("🧠 AI is analyzing your goal..."):
                tasks = st.session_state.goal_agent.decompose_goal(goal_title, goal_desc, custom_instructions)
                if tasks:
                    db = SessionLocal()
                    new_goal = Goal(title=goal_title, description=goal_desc, target_date=target_date, user_id=current_user_id)
                    db.add(new_goal)
                    db.flush()
                    
                    for sub in tasks:
                        new_t = Task(
                            goal_id=new_goal.id,
                            title=sub['title'],
                            description=sub['description'],
                            difficulty=sub.get('difficulty', 2),
                            priority=sub.get('priority', 2),
                            category=sub.get('category', 'General'),
                            due_date=date.today(),
                            user_id=current_user_id
                        )
                        db.add(new_t)
                    db.commit()
                    db.close()
                    
                    st.balloons()
                    st.success(f"🎉 Generated {len(tasks)} actionable tasks for your goal!")
                    
                    # Display generated tasks
                    st.markdown("<h3 style='margin-top: 20px;'>📋 Generated Tasks:</h3>", unsafe_allow_html=True)
                    for i, task in enumerate(tasks, 1):
                        difficulty_stars = "⭐" * task.get('difficulty', 2)
                        st.markdown(f"""
                            <div class="task-card" style="animation: fadeIn 0.5s ease {i * 0.1}s both;">
                                <div style="background: linear-gradient(135deg, #a855f7, #00d4ff); width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-weight: bold;">{i}</div>
                                <div style="flex: 1;">
                                    <div class="task-title">{task['title']}</div>
                                    <div class="task-desc">{task['description']}</div>
                                    <div style="display: flex; gap: 10px; margin-top: 8px; align-items: center;">
                                        <span style="font-size: 0.8rem; color: rgba(255,255,255,0.5);">Difficulty: {difficulty_stars}</span>
                                        <span style="background: rgba(0, 212, 255, 0.1); color: #00d4ff; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem;">{task.get('category', 'General')}</span>
                                    </div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)

    # View Goals
    st.markdown("<h3 style='margin-top: 40px;'>🎯 Current Goals</h3>", unsafe_allow_html=True)
    db = SessionLocal()
    goals = db.query(Goal).filter(Goal.user_id == current_user_id).order_by(Goal.id.desc()).all()
    
    if goals:
        for g in goals:
            # Calculate progress
            total_tasks = db.query(Task).filter(Task.goal_id == g.id).count()
            completed_tasks = db.query(Task).filter(Task.goal_id == g.id, Task.status == "Completed").count()
            progress = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            
            st.markdown(f"""
                <div class="glass-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h4 style="margin: 0; color: #fff;">{g.title}</h4>
                            <p style="margin: 5px 0 0 0; color: rgba(255,255,255,0.5); font-size: 0.9rem;">Target: {g.target_date}</p>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 1.5rem; font-weight: bold; color: #00d4ff;">{progress:.0f}%</div>
                            <div style="font-size: 0.8rem; color: rgba(255,255,255,0.5);">{completed_tasks}/{total_tasks} tasks</div>
                        </div>
                    </div>
                    <div style="margin-top: 15px; background: rgba(255,255,255,0.1); border-radius: 10px; height: 8px; overflow: hidden;">
                        <div style="width: {progress}%; height: 100%; background: linear-gradient(90deg, #a855f7, #00d4ff); border-radius: 10px; transition: width 0.5s ease;"></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <div class="glass-card" style="text-align: center; padding: 40px;">
                <p style="font-size: 1.2rem; color: rgba(255,255,255,0.5);">No goals yet. Create your first goal above! 🚀</p>
            </div>
        """, unsafe_allow_html=True)
    db.close()

# --- Achievements ---
elif menu == "Achievements":
    st.title("🏆 Achievements & Badges")
    st.markdown("<p style='color: rgba(255,255,255,0.6); margin-top: -10px;'>Unlock badges by completing tasks and maintaining streaks</p>", unsafe_allow_html=True)
    
    db = SessionLocal()
    badges = db.query(Badge).all()
    
    cols = st.columns(3)
    for i, b in enumerate(badges):
        with cols[i % 3]:
            is_unlocked = b.unlocked_at is not None
            card_class = "badge-card unlocked" if is_unlocked else "badge-card"
            icon_class = "" if is_unlocked else "badge-locked"
            
            st.markdown(f"""
                <div class="{card_class}">
                    <span class="badge-icon {icon_class}">{b.icon}</span>
                    <h4 style="margin: 10px 0 5px 0; color: {'#fff' if is_unlocked else 'rgba(255,255,255,0.4)'};">{b.name}</h4>
                    <p style="font-size: 0.85rem; color: rgba(255,255,255,0.5); margin: 0;">{b.description}</p>
                    <p style="font-size: 0.75rem; margin-top: 10px; color: {'#10b981' if is_unlocked else 'rgba(255,255,255,0.3)'};">
                        {"🔓 Unlocked: " + str(b.unlocked_at) if is_unlocked else "🔒 Locked"}
                    </p>
                </div>
            """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
    
    db.close()
    
    # Achievement stats
    st.markdown("<h3 style='margin-top: 20px;'>📊 Your Stats</h3>", unsafe_allow_html=True)
    db = SessionLocal()
    total_completed = db.query(Task).filter(Task.status == "Completed", Task.user_id == current_user_id).count()
    total_goals = db.query(Goal).filter(Goal.user_id == current_user_id).count()
    unlocked_badges = db.query(Badge).filter(Badge.unlocked_at != None).count()
    total_badges = db.query(Badge).count()
    db.close()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-value">{total_completed}</div>
                <div class="kpi-label">Tasks Completed</div>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-value">{total_goals}</div>
                <div class="kpi-label">Goals Set</div>
            </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-value">{unlocked_badges}/{total_badges}</div>
                <div class="kpi-label">Badges Unlocked</div>
            </div>
        """, unsafe_allow_html=True)
