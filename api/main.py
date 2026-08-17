import os
import requests
import json
from http.server import BaseHTTPRequestHandler

def search_google_cse(query):
    api_key = os.environ.get("GOOGLE_API_KEY")
    cse_id = os.environ.get("GOOGLE_CSE_ID")
    
    if not api_key or not cse_id:
        return [{"snippet": "Backend variables configuration alert: Check GOOGLE_API_KEY / GOOGLE_CSE_ID in Vercel settings.", "link": ""}]
    
    url = "https://googleapis.com"
    params = {
        "key": api_key,
        "cx": cse_id,
        "q": query,
        "num": 4
    }
    
    try:
        res = requests.get(url, params=params, timeout=5)
        items = res.json().get("items", [])
        results = []
        for item in items:
            results.append({
                "title": item.get("title", "Official Portal Page"),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", "")
            })
        return results if results else [{"snippet": "No recent updates matching this query found on the official portals.", "link": ""}]
    except Exception as e:
        return [{"snippet": f"Search execution failed: {str(e)}", "link": ""}]

def generate_ai_reply(query, context_list):
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        return "Backend deployment missing GEMINI_API_KEY environment configuration variable."

    context_str = ""
    for idx, ctx in enumerate(context_list):
        context_str += f"[Source {idx+1}]: {ctx['snippet']}\n"

    prompt = (
        f"You are the conversational Telangana Higher Education AI Assistant for Nagarjuna Govt College.\n"
        f"You must strictly use the provided official search context to answer the user's question.\n"
        f"Never guess or make up data, deadlines, or fees. If the details are not explicitly present in the data, "
        f"state clearly that it isn't listed in recent notices and advise them to use the linked official links.\n\n"
        f"Context from Telangana Official Sites:\n{context_str}\n\n"
        f"Student Query: {query}\n\n"
        f"Provide a friendly, highly professional, markdown-formatted response:"
    )

    url = f"https://googleapis.com{gemini_key}"
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=8)
        return res.json()['candidates']['content']['parts']['text']
    except Exception as e:
        return f"AI generation bottleneck encountered. Details: {str(e)}"

# The class name must be lowercase 'handler' for Vercel Serverless Architecture
class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "NGC AI Engine Operational"}).encode('utf-8'))
        return

    def do_POST(self):
        # We process the request directly without strict path routing checks
        content_length = int(self.headers['Content-Length'])
        req_body = json.loads(self.rfile.read(content_length).decode('utf-8'))
        user_query = req_body.get('message', '')

        if not user_query:
            self.send_response(400)
            self.end_headers()
            return

        sources = search_google_cse(user_query)
        ai_reply = generate_ai_reply(user_query, sources)
        valid_sources = [s for s in sources if s['link']]

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        
        self.wfile.write(json.dumps({
            "reply": ai_reply,
            "sources": valid_sources
        }).encode('utf-8'))
        return

