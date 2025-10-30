import os
from dotenv import load_dotenv
from google import genai
from google.genai import types  # type: ignore
from googleapiclient.discovery import build

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
SERP_API_KEY = os.getenv("SERP_API_KEY")
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

grounding_tool = types.Tool(
    google_search=types.GoogleSearch()
)

config = types.GenerateContentConfig(
    tools=[grounding_tool],
    temperature=0.2,
    system_instruction=(
        '''
            Hi, you are a smart shopping assistant. Every single decision you make 
            should be based on finding the best, factual, unbiased information on what
            a user wants to buy. This also applies to specific features/attributes of a product
            they may be looking for. Always:
                - Avoid opening/closing remarks, or fluffy ai intros/outros. Go straight to point.
                - Back your statements with factual information from your tools.
                - Respond in a clear, concise language.
                - Make use of the metadata provided in the user's prompt, it gives you context
                on the task at hand.
        '''
    ),
)
