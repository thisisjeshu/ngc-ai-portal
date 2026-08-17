import os
import requests
import json
import re
from http.server import BaseHTTPRequestHandler

def sanitize_user_input(text):
    if not text:
        return ""
    # Remove potentially breaking markdown injection tags
    clean_text = re.sub(r'[<>{}\[\]\\^\`|~]', '', text)
    return clean_text.strip()[:300]

def search_google_cse(query):
    api_key = os.environ.get("GOOGLE_API_KEY")
    cse_id = os.environ.get("GOOGLE_CSE_ID")
    
    if not api_key or not cse_id:
        return [{"snippet": "Configuration variables verification alert: Check your keys in Vercel settings.", "link": ""}]
    
    url = "https://googleapis.com"
    params = {
        "key": api_key,
        "cx": cse_id,
        "q": query,
        "num": 3
    }
    
    try:
        res = requests.get(url, params=params, timeout=5)
        # Prevent crash if response doesn't contain items
        if res.status_code != 200:
            return [{"snippet": f"Google API returned error status {res.status_code}", "link": ""}]
            
        items = res.json().get("items", [])
        if not items:
            return [{"snippet": "No updates matching this query are listed on official portals.", "link": ""}]
            
        results = []
        for item in items:
            results.append({
                "title": item.get("title", "Official Page Reference"),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", "")
            })
        return results
    except Exception as e:
        return [{"snippet": f"Search engine temporarily unavailable: {str(e)}", "link": ""}]

def generate_ai_reply(query, context_list):
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        return "Backend deployment error: Missing GEMINI_API_KEY variable configuration."

    context_str = ""
    for idx, ctx in enumerate(context_list):
        context_str += f"[Source {idx+1}]: {ctx['snippet']}\n"

    prompt = (
        f"You are the professional Higher Education AI Assistant for Nagarjuna Government College, Nalgonda.\n"
        f"You must strictly use the provided official context snippets to answer the user's question.\n"
        f"Never invent deadlines, fees, or metrics. If details are not explicitly present, advise them to use the provided links.\n\n"
        f"Official Context Data:\n{context_str}\n\n"
        f"Student Query: {query}\n\n"
        f"Provide a friendly, conversational response:"
    )

    # Secure endpoint template
    url = f"https://googleapis.com{gemini_key}"
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=8)
        res_json = res.json()
        
        # Check for quota limits or API blocks explicitly to surface errors safely
        if 'candidates' in res_json and len(res_json['candidates']) > 0:
            return res_json['candidates'][0]['content']['parts'][0]['text']
        elif 'error' in res_json:
            return f"Gemini API returned an alert: {res_json['error'].get('message', 'Unknown Error')}"
        else:
            return "The AI engine could not parse a valid output content string. Please re-submit your query."
    except Exception as e:
        return f"AI communication link exception occurred: {str(e)}"

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            try:
                current_dir = os.path.dirname(os.path.abspath(__file__))
                html_path = os.path.join(current_dir, 'index.html')
                with open(html_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.wfile.write(content.encode('utf-8'))
            except Exception as e:
                self.wfile.write(f"HTML Core Render Error: {str(e)}".encode('utf-8'))
            return

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "NGC AI Engine Operational"}).encode('utf-8'))
        return

    def do_POST(self):
        if self.path != '/api/main' and self.path != '/main':
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers['Content-Length'])
        req_body = json.loads(self.rfile.read(content_length).decode('utf-8'))
        raw_query = req_body.get('message', '')
        sanitized_query = sanitize_user_input(raw_query)

        if not sanitized_query:
            self.send_response(400)
            self.end_headers()
            return

        sources = search_google_cse(sanitized_query)
        ai_reply = generate_ai_reply(sanitized_query, sources)
        valid_sources = [s for s in sources if s.get('link')]

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        
        self.wfile.write(json.dumps({
            "reply": ai_reply,
            "sources": valid_sources
        }).encode('utf-8'))
        return



