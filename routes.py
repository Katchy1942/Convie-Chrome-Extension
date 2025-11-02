from flask import jsonify, request, Blueprint
from config import client, config, youtube, SERP_API_KEY
import json
import requests
import traceback

routes = Blueprint('routes', __name__)

def search_youtube(keyword, max_results=2):
    try:
        request_yt = youtube.search().list(
            part='snippet',
            q=keyword,
            type='video',
            maxResults=2,
            order='relevance'
        )
        response = request_yt.execute()
        
        videos = []
        for item in response.get('items', [])[:2]:
            videos.append({
                'video_id': item['id']['videoId'],
                'title': item['snippet']['title'],
                'channel': item['snippet']['channelTitle'],
                'url': f"https://www.youtube.com/watch?v={item['id']['videoId']}",
                'thumbnail': item['snippet']['thumbnails']['default']['url']
            })
        return videos
    except Exception as e:
        print(f"YouTube search error: {e}")
        return []

def search_shopping(keyword, max_results=10):
    try:
        params = {
            "engine": "google_shopping",
            "q": keyword,
            "api_key": SERP_API_KEY,
            "num": max_results
        }
        
        response = requests.get("https://serpapi.com/search", params=params)
        data = response.json()
        
        products = []
        for product in data.get("shopping_results", [])[:max_results]:
            products.append({
                'title': product.get('title'),
                'price': product.get('price'),
                'link': product.get('product_link'),
                'thumbnail': product.get('thumbnail'),
                'source': product.get('source')
            })
        return products
    except Exception as e:
        print(f"Shopping search error: {e}")
        return []

@routes.route('/', methods=['POST'])
def home():
    data = request.get_json()
    item = data.get('latest')

    if not item:
        return jsonify({"error": "No data provided"}), 400

    page_url = item.get('url')
    title = item.get('pageTitle')
    description = item.get('pageDescription')
    selected_text = item.get('selectedText')
    full_context = item.get('fullContext')
    time_date = item.get('timestamp')

    prompt = f"""
        A user on this page {page_url} which does this {description}
        highlighted a text "{selected_text}". You are to output information in this EXACT format:

        {{
            "type": "[if {selected_text} contains a product or feature, set to a 'product' or 'feature', else 'other']",
            "youtube_search_keyword": "[a single keyword or group of words to find a relevant YouTube video about {selected_text}]",
            "similar_products_keyword": "[a single keyword or group of words to find similar products or features on the web]",
            "summary": "[About 4 sentences explaining what {selected_text} is.]",

            "reviews": [
                "[Review insight 1]",
                "[Review insight 2]"
            ],

            "cons": [
                "[Con 1]",
                "[Con 2]",
                "[Con 3]",
                "[Con 4]",
                "[Con 5]"
            ],

            "workarounds_and_maintenance": [
                "[Tip 1]",
                "[Tip 2]",
                "[Tip 3]",
                "[Tip 4]",
                "[Tip 5]",
                "[Tip 6]"
            ]
        }}

        Reviews should be a summary of insights from the web. Cons are the factors that would prevent
        the user from getting adequate value, or comfort. Workarounds and Maintenance are simply tooltips.
        In the case of 'other', just provide generic information about the highlighted text while following
        the format above.

        You might need these for context:
        Time and Date: {time_date},
        Full Context: {full_context},
        Page Title: {title},
        Page Description: {description}
        
        Return ONLY valid JSON, no markdown formatting or extra text.
    """

    print('Fetching AI response...')

    try:
        response = client.models.generate_content(
            model='gemini-2.5-pro',
            contents=prompt,
            config=config
        )
        
        ai_response = response.text.strip()
        
        if ai_response.startswith('```json'):
            ai_response = ai_response[7:]
        elif ai_response.startswith('```'):
            ai_response = ai_response[3:]
        if ai_response.endswith('```'):
            ai_response = ai_response[:-3]
        
        ai_response = ai_response.strip()
        result = json.loads(ai_response)
        
        print("Main AI response parsed successfully.")
        
        print("Fetching YouTube keyword...")
        if result.get("youtube_search_keyword"):
            youtube_keyword = result["youtube_search_keyword"]
        else:
            youtube_keyword = selected_text
        
        print("Fetching similar products keyword...")
        if result.get("similar_products_keyword"):
            similar_keyword = result["similar_products_keyword"]
        else:
            similar_keyword = selected_text
        
        print(f"Searching YouTube for: {youtube_keyword}")
        result["youtube_videos"] = search_youtube(youtube_keyword, max_results=5)
        
        print(f"Searching products for: {similar_keyword}")
        result["similar_products"] = search_shopping(similar_keyword, max_results=10)
        
        print("All responses fetched successfully.")
        return jsonify(result), 200
        
    except json.JSONDecodeError as e:
        print(traceback.format_exc())
        return jsonify({
            "error": "Failed to parse AI response",
            "details": str(e),
            "raw_response": ai_response
        }), 500
        
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({
            "error": "Failed to generate content",
            "details": str(e)
        }), 500