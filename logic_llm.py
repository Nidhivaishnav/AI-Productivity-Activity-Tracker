import os
import json
import re
from typing import List, Dict
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv

load_dotenv()

class GoalAgent:
    def __init__(self):
        # Use demo mode if API key is missing or is a placeholder
        api_key = os.getenv("OPENAI_API_KEY")
        # Check if it's a real key (starts with 'sk-') or just a placeholder
        if api_key and api_key.startswith("sk-") and len(api_key) > 20:
            self.llm = ChatOpenAI(model="gpt-4o", api_key=api_key)
        else:
            self.llm = None  # Demo mode

    def decompose_goal(self, goal_title: str, goal_description: str) -> List[Dict]:
        """
        Breaks down a long-term goal into daily actionable tasks.
        """
        if not self.llm:
            # Demo mode: Generate relevant sample tasks based on goal
            return [
                {"title": f"Research fundamentals of {goal_title}", "description": "Gather resources, tutorials, and create a learning roadmap", "difficulty": 2, "priority": 3},
                {"title": f"Set up environment for {goal_title}", "description": "Install necessary tools, create workspace, bookmark resources", "difficulty": 2, "priority": 3},
                {"title": f"Complete beginner exercises for {goal_title}", "description": "Start with basic concepts and hands-on practice", "difficulty": 3, "priority": 2},
                {"title": f"Build a small project for {goal_title}", "description": "Apply learned concepts in a practical mini-project", "difficulty": 4, "priority": 2},
                {"title": f"Review and practice {goal_title} concepts", "description": "Revisit difficult topics and strengthen understanding", "difficulty": 3, "priority": 2},
                {"title": f"Advanced topics in {goal_title}", "description": "Explore complex concepts and edge cases", "difficulty": 5, "priority": 1}
            ]

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a highly efficient productivity assistant. You help users break down their long-term goals into actionable daily tasks."),
            ("human", """The user has a long-term goal: {title}
Description: {description}

Break this goal down into 5-7 actionable, concrete daily tasks that can be completed one by one.

Return your response as a JSON array of tasks. Each task should have:
- "title": a short task title
- "description": a brief description of what to do
- "difficulty": a number from 1-5 (1=easy, 5=hard)
- "priority": a number from 1-3 (1=low, 3=high)

Return ONLY the JSON array, no other text. Example format:
[
  {{"title": "Task 1", "description": "Do something", "difficulty": 2, "priority": 3}},
  {{"title": "Task 2", "description": "Do another thing", "difficulty": 1, "priority": 2}}
]""")
        ])

        # Use chain syntax with StrOutputParser for clean output
        chain = prompt | self.llm | StrOutputParser()
        
        try:
            response = chain.invoke({
                "title": goal_title,
                "description": goal_description
            })
            
            # Extract JSON from the response (handle markdown code blocks if present)
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                tasks = json.loads(json_match.group())
                return tasks
            else:
                print(f"Could not find JSON array in response: {response}")
                return []
                
        except Exception as e:
            print(f"Error in LLM call or parsing: {e}")
            return []

class PrioritizerAgent:
    """
    An agent that can suggest which tasks to focus on based on difficulty and priority.
    """
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        self.llm = ChatOpenAI(model="gpt-4o", api_key=api_key) if api_key else None

    def suggest_priority(self, tasks: List[Dict]) -> List[Dict]:
        # Implementation for adaptive scheduling
        # For now, it just sorts by priority (desc) and difficulty (asc)
        return sorted(tasks, key=lambda x: (-x.get('priority', 1), x.get('difficulty', 1)))
