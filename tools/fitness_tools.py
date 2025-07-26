import re
import os
import random
from langchain.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults

@tool
def calculate_diet_plan(goal: str, weight_kg: float, height_cm: float, age: int, gender: str, activity_level: str):
    """
    Calculates a personalized 7-day diet plan including daily calorie and macronutrient targets.
    'goal' must be one of: 'weight_loss', 'maintenance', 'muscle_gain'.
    'activity_level' must be one of: 'sedentary', 'light', 'moderate', 'active'.
    """
    # BMR Calculation
    if gender.lower() == 'male':
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161

    activity_multipliers = {'sedentary': 1.2, 'light': 1.375, 'moderate': 1.55, 'active': 1.725}
    calories = bmr * activity_multipliers.get(activity_level.lower(), 1.55)

    if goal == 'weight_loss':
        calories -= 400
        macros = {'protein_g': 1.8 * weight_kg, 'carbs_g': 150, 'fat_g': (calories * 0.25) / 9}
    elif goal == 'muscle_gain':
        calories += 400
        macros = {'protein_g': 2.0 * weight_kg, 'carbs_g': (calories * 0.4) / 4, 'fat_g': (calories * 0.3) / 9}
    else: # maintenance
        macros = {'protein_g': 1.8 * weight_kg, 'carbs_g': (calories * 0.45) / 4, 'fat_g': (calories * 0.25) / 9}

    # Dummy 7-day meal plan for demonstration
    meal_plan_by_day = [
        {"Day": "Monday", "Breakfast": "Oatmeal & Berries", "Lunch": "Grilled Chicken Salad", "Dinner": "Salmon & Veggies"},
        {"Day": "Tuesday", "Breakfast": "Scrambled Eggs", "Lunch": "Quinoa Bowl", "Dinner": "Lentil Soup"},
        {"Day": "Wednesday", "Breakfast": "Greek Yogurt & Nuts", "Lunch": "Leftover Salmon", "Dinner": "Turkey Stir-fry"},
        {"Day": "Thursday", "Breakfast": "Protein Smoothie", "Lunch": "Leftover Stir-fry", "Dinner": "Chicken Fajitas"},
        {"Day": "Friday", "Breakfast": "Oatmeal & Berries", "Lunch": "Tuna Salad Sandwich", "Dinner": "Lean Steak & Asparagus"},
        {"Day": "Saturday", "Breakfast": "Pancakes (Protein)", "Lunch": "Leftover Steak", "Dinner": "Healthy Pizza"},
        {"Day": "Sunday", "Breakfast": "Scrambled Eggs", "Lunch": "Large Salad", "Dinner": "Roast Chicken"},
    ]

    return {
        "daily_calories": round(calories),
        "macros": {k: round(v) for k, v in macros.items()},
        "weekly_meal_plan": meal_plan_by_day
    }

@tool
def generate_workout_schedule(goal: str, experience_level: str):
    """Generates a detailed 7-day workout schedule."""
    if goal == "muscle_gain":
        return [
            {"Day": "Monday", "Workout Type": "Upper Body Strength", "Example Exercises": "3x5 Bench Press, 3x8 Rows"},
            {"Day": "Tuesday", "Workout Type": "Lower Body Strength", "Example Exercises": "3x5 Squats, 1x5 Deadlifts"},
            {"Day": "Wednesday", "Workout Type": "Active Recovery", "Example Exercises": "30 min walk or stretching"},
            {"Day": "Thursday", "Workout Type": "Upper Body Hypertrophy", "Example Exercises": "4x12 Incline Press, 4x15 Lat Pulldowns"},
            {"Day": "Friday", "Workout Type": "Lower Body Hypertrophy", "Example Exercises": "4x12 Lunges, 4x15 Leg Curls"},
            {"Day": "Saturday", "Workout Type": "Full Body / Cardio", "Example Exercises": "30 mins moderate cardio, planks"},
            {"Day": "Sunday", "Workout Type": "Rest", "Example Exercises": "Full rest day"},
        ]
    else: # weight_loss or maintenance
        return [
            {"Day": "Monday", "Workout Type": "Full Body Strength", "Example Exercises": "3x10 Goblet Squats, 3x12 Push-ups"},
            {"Day": "Tuesday", "Workout Type": "HIIT Cardio", "Example Exercises": "20 mins: 30s sprint, 60s rest"},
            {"Day": "Wednesday", "Workout Type": "Active Recovery", "Example Exercises": "30 min walk"},
            {"Day": "Thursday", "Workout Type": "Full Body Strength", "Example Exercises": "3x10 Overhead Press, 3x12 Lunges"},
            {"Day": "Friday", "Workout Type": "Steady-State Cardio", "Example Exercises": "45 mins jogging or cycling"},
            {"Day": "Saturday", "Workout Type": "Core & Flexibility", "Example Exercises": "3 sets of leg raises, planks"},
            {"Day": "Sunday", "Workout Type": "Rest", "Example Exercises": "Full rest day"},
        ]


@tool
def find_youtube_workout_video(workout_type: str):
    """
    Searches the web (via Tavily) for a relevant YouTube workout video and returns a clickable Markdown link.
    """
    try:
        tavily_search = TavilySearchResults(api_key=os.getenv("TAVILY_API_KEY"))
        query = f"'{workout_type}' workout video youtube.com"
        results = tavily_search.invoke({"query": query})

        if not results:
            return "Could not find any relevant search results for a video."

        # Loop through results to find the first valid YouTube link
        for res_dict in results:
            url_to_check = res_dict.get('url', '')
            title = res_dict.get('title', f"{workout_type} Workout Video")

            # Check if the URL is a valid YouTube link
            if "youtube.com/watch" in url_to_check or "youtu.be/" in url_to_check:
                # Format as a Markdown link
                formatted_link = f"[{title}]({url_to_check})"
                return formatted_link

        return "Could not find a direct YouTube video link in search results."
    except Exception as e:
        return f"Could not find a video link due to an error: {e}"


@tool
def get_calories_for_food(food_item: str):
    """
    Performs a live web search to find the calorie count for a given food item using Tavily.
    """
    try:
        tavily_search = TavilySearchResults(api_key=os.getenv("TAVILY_API_KEY"))
        query = f"calories in {food_item}"
        results = tavily_search.invoke({"query": query})

        if not results:
            return "Could not find calorie information."

        if results and results[0].get('content'):
            return results[0]['content']

        return "Could not find calorie information in the search results."
    except Exception as e:
        return f"Could not find calorie information due to an error: {e}"


@tool
def get_motivational_content(topic: str = "general_fitness"):
    """Provides a famous motivational quote and a fitness fact."""
    quotes = [{"quote": "The only bad workout is the one that didn't happen.", "author": "Unknown"}]
    facts = ["Fact: Regular exercise has been shown to improve mood and reduce feelings of anxiety and depression."]
    return {"quote": random.choice(quotes), "fact": random.choice(facts)}
