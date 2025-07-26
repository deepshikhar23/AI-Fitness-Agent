from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain import hub
from dotenv import load_dotenv

# Import all our new and updated tools
from tools.fitness_tools import (
    calculate_diet_plan,
    generate_workout_schedule,
    get_calories_for_food,
    get_motivational_content,
    find_youtube_workout_video,
)

load_dotenv()

def create_agent():
    """
    Initializes and returns the AI Fitness Agent with all its tools.
    """
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
    
    # The complete list of our agent's "superpowers"
    tools = [
        calculate_diet_plan,
        generate_workout_schedule,
        get_calories_for_food,
        get_motivational_content,
        find_youtube_workout_video,
    ]
    
    prompt = hub.pull("hwchase17/structured-chat-agent")

    agent = create_structured_chat_agent(llm=llm, tools=tools, prompt=prompt)

    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=15, # Increased for the multi-step plan generation
    )

    return agent_executor
