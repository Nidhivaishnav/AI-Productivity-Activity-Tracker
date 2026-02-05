# AI Productivity & Activity Tracker

This is a production-level productivity application built entirely in Python. It leverages LLMs for goal planning and Machine Learning for productivity forecasting.

## Features
- **AI Goal Planner**: Uses LangChain and GPT-4o to break down long-term goals into daily tasks.
- **Productivity Analytics**: Calculates daily scores and visualizes trends using Plotly.
- **ML Forecasting**: Predicts future productivity levels using Scikit-Learn Linear Regression.
- **Gamification**: Streak tracking and badge unlocking system.
- **Premium UI**: Dark-themed, responsive dashboard built with Streamlit.

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Set your OpenAI API key in `.env`:
   ```
   OPENAI_API_KEY=your_key_here
   ```
3. Run the app:
   ```bash
   streamlit run app.py
   ```

## Tech Stack
- **Frontend**: Streamlit
- **Backend**: Python, SQLAlchemy (SQLite)
- **AI/LLM**: LangChain, OpenAI
- **Data Science/ML**: Pandas, Plotly, Scikit-learn
