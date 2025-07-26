import gradio as gr
import gradio.themes as themes
import uuid
import json
import pandas as pd
import re
from dotenv import load_dotenv

load_dotenv()
from agent.agent_core import create_agent

# --- State Management ---
sessions = {}
def get_session(session_id: str):
    if session_id not in sessions:
        sessions[session_id] = {
            "agent_executor": create_agent(),
            "user_details": {},
            "plan_context": "",
            "chat_history": []
        }
    return sessions[session_id]

# --- Helper Function to Convert Markdown Link to HTML ---
def markdown_to_html_link(markdown_link_str: str) -> str:
    """
    Converts a Markdown link string (e.g., '[Title](URL)') to an HTML <a> tag.
    Returns the original string if not a valid Markdown link.
    """
    if not isinstance(markdown_link_str, str):
        return "" # Handle non-string values gracefully, e.g., None or NaN

    # Regex to find [Link Text](URL) pattern
    match = re.match(r'\[(.*?)\]\((.*?)\)', markdown_link_str)
    if match:
        title = match.group(1)
        url = match.group(2)
        # Use target="_blank" to open link in a new tab
        return f'<a href="{url}" target="_blank">{title}</a>'
    return markdown_link_str # Return original if no match (e.g., "null" or plain text)


# --- Formatting Function ---
def render_plan_from_json(raw_json_string: str):
    try:
        data = json.loads(raw_json_string) if isinstance(raw_json_string, str) else raw_json_string
        
        # Diet Plan Section
        diet_plan = data.get('diet_plan', {})
        macros = diet_plan.get('macros', {})
        diet_md = f"""
        ### 🥗 Your Nutrition Plan
        **Daily Calorie Target:** `{diet_plan.get('daily_calories', 'N/A')} kcal`
        **Macronutrients:**
        - **Protein:** `{macros.get('protein_g', 'N/A')}g`
        - **Carbs:** `{macros.get('carbs_g', 'N/A')}g`
        - **Fat:** `{macros.get('fat_g', 'N/A')}g`
        """
        meal_plan_df = pd.DataFrame(diet_plan.get('weekly_meal_plan', []))

        # Workout Plan Section - MODIFIED TO OUTPUT HTML
        workout_plan_data = data.get('workout_plan', [])
        workout_html_table = "<h3>🏋️ Your Workout Plan</h3>" # Add a header
        if workout_plan_data:
            workout_df = pd.DataFrame(workout_plan_data)
            # Use the existing helper to convert markdown to HTML links
            if 'Video Link' in workout_df.columns:
                workout_df['Video Link'] = workout_df['Video Link'].apply(markdown_to_html_link)
            
            # Convert the DataFrame to an HTML string
            # escape=False is critical to render the <a> tags correctly
            workout_html_table += workout_df.to_html(escape=False, index=False)
        else:
            workout_html_table += "<p>No workout plan generated.</p>"
        
        # Motivation Content
        motivation = data.get('motivational_content', {})
        quote = motivation.get('quote', {})
        quote_text = f"## 🔥 Motivation Zone\n> \"{quote.get('quote', '...')}\" \n> — *{quote.get('author', 'Unknown')}*"
        fact_text = f"💡 **Did you know?** {motivation.get('fact', '...')}"
        
        # Return the HTML string for the workout plan
        return diet_md, meal_plan_df, workout_html_table, quote_text, fact_text, data
    except Exception as e:
        return f"Error formatting plan: {e}", pd.DataFrame(), "", "", "", None

# --- Main Handler Functions ---
def generate_initial_plan(goal, weight, height, age, gender, activity, experience, session_id, progress=gr.Progress(track_tqdm=True)):
    session = get_session(session_id)
    agent_executor = session["agent_executor"]
    
    progress(0, desc="Warming up...")

    session["user_details"] = {
        "goal": goal, "weight_kg": weight, "height_cm": height, "age": age,
        "gender": gender, "activity_level": activity, "experience_level": experience
    }

    initial_prompt = f"""
    My primary goal is {goal}. My details are: {json.dumps(session['user_details'])}.
    
    Your task is to generate a complete and detailed fitness plan. To do this, you MUST perform the following sequence of actions:
    1. Call the `calculate_diet_plan` tool with all the user's details to get their nutrition and 7-day meal plan.
    2. Call the `generate_workout_schedule` tool to get their 7-day workout schedule.
    3. For EACH of the 7 days in the workout schedule that is NOT a rest day, call the `find_youtube_workout_video` tool with the "Workout Type" for that day to find a relevant video link. You must add this link back into the workout schedule data for that day.
    4. Call the `get_motivational_content` tool.
    5. Finally, combine all the results from the tools into a single, final JSON object with keys: 'diet_plan', 'workout_plan', 'motivational_content'.
    """
    
    try:
        progress(0.2, desc="Agent is designing your plan...")
        response = agent_executor.invoke({"input": initial_prompt})
        raw_output = response.get("output", "{}")
        
        progress(0.8, desc="Formatting your beautiful plan...")
        # Note: The third returned value is now an HTML string
        diet_md, meal_plan_df, workout_html, quote_text, fact_text, plan_data = render_plan_from_json(raw_output)
        
        session["plan_context"] = f"Original user details: {json.dumps(session['user_details'])}\n\nGenerated Plan (JSON): {json.dumps(plan_data, indent=2)}"
        
        initial_chat_message = {"role": "assistant", "content": "Ask me anything related to Fitness. like:\n\n- 'What are the benefits of a Full Body Strength workout?'\n- 'Find calories for a banana.'\n- 'Tell me another motivational quote.'\n- 'Can you adjust my diet plan for 1600 calories?'"}

        tab_switch = gr.Tabs(selected=1)
        
        # Return the HTML string to the output component
        return diet_md, meal_plan_df, workout_html, quote_text, fact_text, tab_switch, [initial_chat_message]
        
    except Exception as e:
        error_message = f"An error occurred: {e}"
        # Return an empty string for the HTML component on error
        return error_message, pd.DataFrame(), "", "", "", gr.update(), []

def respond_in_chat(user_message, chat_history, session_id):
    session = get_session(session_id)
    agent_executor = session["agent_executor"]
    chat_history.append({"role": "user", "content": user_message})
    
    contextual_prompt = f"""
    Context: {session.get('plan_context', 'No plan generated yet.')}
    User's new request: "{user_message}"
    Based on the context and the new request, generate an updated JSON plan if needed, or answer the question textually.
    """
    try:
        response = agent_executor.invoke({"input": contextual_prompt})
        bot_message_raw = response.get("output", "Sorry, I had trouble.")
        chat_history.append({"role": "assistant", "content": bot_message_raw})
    except Exception as e:
        chat_history.append({"role": "assistant", "content": f"An error occurred: {e}"})

    return chat_history

def handle_calorie_lookup(food_item, session_id):
    session = get_session(session_id)
    return session["agent_executor"].invoke({"input": f"Use your tool to find the calories for '{food_item}'"}).get("output")

# --- Gradio UI ---
with gr.Blocks(theme=themes.Soft(primary_hue="lime"), title="AI Fitness Architect") as demo:
    session_id = gr.State(lambda: str(uuid.uuid4()))

    gr.Markdown("# 🤖 AI Fitness Architect")
    
    with gr.Tabs() as tabs:
        with gr.TabItem("1. Your Details", id=0):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### Enter your details to generate a plan.")
                    goal = gr.Dropdown(label="Primary Goal", choices=["weight_loss", "maintenance", "muscle_gain"], value="weight_loss")
                    weight = gr.Number(label="Weight (kg)", value=85)
                    height = gr.Number(label="Height (cm)", value=180)
                    age = gr.Number(label="Age", value=32)
                    gender = gr.Dropdown(label="Gender", choices=["male", "female"], value="male")
                    activity = gr.Dropdown(label="Activity Level", choices=["sedentary", "light", "moderate", "active"], value="light")
                    experience = gr.Dropdown(label="Experience Level", choices=["beginner", "intermediate", "advanced"], value="beginner")
                    generate_btn = gr.Button("🚀 Generate My Plan", variant="primary")
                with gr.Column(scale=2):
                    gr.Markdown("### Your Generated Plan")
                    plan_output_diet = gr.Markdown("Your plan will appear here...")
                    plan_output_meal_plan = gr.DataFrame(label="Weekly Meal Plan", interactive=False)
                    # *** MODIFIED to gr.HTML ***
                    plan_output_workout = gr.HTML(label="Weekly Workout Schedule") 

        with gr.TabItem("2. Customize & Chat", id=1):
            chatbot_display = gr.Chatbot(label="Conversation", type="messages", height=500, avatar_images=(None, "https://i.imgur.com/9kQ1Abw.png"))
            chat_input_box = gr.Textbox(lines=1, placeholder="e.g., 'Can you replace jogging with something else?'", label="Chat")

        with gr.TabItem("3. Tools & Info", id=2):
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### 🧮 Calorie Calculator")
                    food_input = gr.Textbox(label="Enter a food item (e.g., 'apple')", scale=3)
                    lookup_btn = gr.Button("Calculate")
                    calorie_output = gr.Textbox(label="Estimated Calories", interactive=False)
                with gr.Column():
                    gr.Markdown("### 🔥 Motivation Zone")
                    quote_display = gr.Markdown("*Your inspirational quote will appear here...*")
                    fact_display = gr.Markdown("*Your fitness fact will appear here...*")

    # Event Handlers
    # Note: The third output now corresponds to the gr.HTML component
    generate_btn.click(
        generate_initial_plan,
        inputs=[goal, weight, height, age, gender, activity, experience, session_id],
        outputs=[plan_output_diet, plan_output_meal_plan, plan_output_workout, quote_display, fact_display, tabs, chatbot_display]
    )
    chat_input_box.submit(respond_in_chat, inputs=[chat_input_box, chatbot_display, session_id], outputs=[chatbot_display]).then(lambda: "", outputs=[chat_input_box])
    lookup_btn.click(handle_calorie_lookup, inputs=[food_input, session_id], outputs=[calorie_output])

if __name__ == "__main__":
    demo.launch(debug=True)