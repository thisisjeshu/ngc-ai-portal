import os
import requests
import json
import re
from http.server import BaseHTTPRequestHandler

def sanitize_user_input(text):
    if not text:
        return ""
    # Strip dangerous layout control parameters
    clean_text = re.sub(r'[<>{}\[\]\\^\`|~]', '', text)
    return clean_text.strip()[:300]

def search_google_cse(query):
    api_key = os.environ.get("GOOGLE_API_KEY")
    cse_id = os.environ.get("GOOGLE_CSE_ID")
    
    if not api_key or not cse_id:
        return [{"snippet": "Configuration verification warning: Check your parameters in Vercel settings.", "link": ""}]
    
    url = "https://googleapis.com"
    params = {
        "key": api_key,
        "cx": cse_id,
        "q": query,
        "num": 3
    }
    
    try:
        res = requests.get(url, params=params, timeout=5)
        if res.status_code != 200:
            return [{"snippet": "Official documentation search throttle ceiling reached.", "link": ""}]
        items = res.json().get("items", [])
        if not items:
            return [{"snippet": "No updates matching this timeline criteria are listed on official portals.", "link": ""}]
        
        results = []
        for item in items:
            results.append({
                "title": item.get("title", "Official Reference"),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", "")
            })
        return results
    except Exception:
        return [{"snippet": "Official indices temporarily offline.", "link": ""}]

def generate_ai_reply(query, context_list):
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        return "Backend deployment missing GEMINI_API_KEY variable configuration."

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
        f"Provide a friendly, highly professional, conversational response:"
    )

    # FIXED: Clean, hardcoded endpoint parameters to block extraction loops
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    target_endpoint = "https://googleapis.com"

    try:
        # Pass the key explicitly as an independent query argument parameter
        res = requests.post(f"{target_endpoint}?key={gemini_key}", headers=headers, json=payload, timeout=8)
        res_json = res.json()
        
        if 'candidates' in res_json and len(res_json['candidates']) > 0:
            return res_json['candidates']['content']['parts']['text']
        else:
            return "The AI engine could not finalize a content string parsing task. Please re-submit your query."
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
                    self.wfile.write(f.read().encode('utf-8'))
            except Exception as e:
                self.wfile.write(f"HTML Resource Read Failure: {str(e)}".encode('utf-8'))
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



