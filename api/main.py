import os
import requests
import json
import re
from http.server import BaseHTTPRequestHandler

def sanitize_user_input(text):
    if not text:
        return ""
    clean_text = re.sub(r'[<>{}\[\]\\^\`|~]', '', text)
    return clean_text.strip()[:300]

def search_google_cse(query):
    # Change these two lines to look for your fresh NGC_ prefixes
    api_key = os.environ.get("NGC_GOOGLE_API_KEY", "").strip()
    cse_id = os.environ.get("NGC_GOOGLE_CSE_ID", "").strip()
    
    if not api_key or not cse_id:
        return [{"snippet": "Configuration Alert: Provide NGC_GOOGLE_API_KEY and NGC_GOOGLE_CSE_ID variables in Vercel settings.", "link": ""}]
    
    # Completely hardcoded baseline URL path
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
            return [{"snippet": f"Google Search Engine returned error code {res.status_code}", "link": ""}]
        items = res.json().get("items", [])
        if not items:
            return [{"snippet": "No updates matching this criteria are listed on official portals.", "link": ""}]
        return [{"title": i.get("title", "Reference"), "link": i.get("link", ""), "snippet": i.get("snippet", "")} for i in items]
    except Exception as e:
        return [{"snippet": f"Search engine offline: {str(e)}", "link": ""}]


        
        results = []
        for item in items:
            results.append({
                "title": item.get("title", "Official Reference"),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", "")
            })
        return results
    except Exception as e:
        return [{"snippet": f"Official indices connection check error: {str(e)}", "link": ""}]

def generate_ai_reply(query, context_list):
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        return "Backend deployment missing GEMINI_API_KEY variable configuration."

    context_str = ""
    for idx, ctx in enumerate(context_list):
        context_str += f"[Source {idx+1}]: {ctx['snippet']}\n"

    # Upgraded, robust prompt system instruction layout
    prompt = (
        f"You are the conversational Telangana Higher Education AI Assistant for Nagarjuna Govt College.\n"
        f"You must strictly use the provided official search context to answer the user's question.\n"
        f"Never guess or make up data, deadlines, or fees. If the details are not explicitly present in the data, "
        f"state clearly that it isn't listed in recent notices and advise them to use the linked official links.\n\n"
        f"Context from Telangana Official Sites:\n{context_str}\n\n"
        f"Student Query: {query}\n\n"
        f"Provide a friendly, highly professional, conversational response:"
    )

    # RECONFIGURED: Use stable production API version endpoint paths
    url = f"https://googleapis.com{gemini_key}"
    headers = {"Content-Type": "application/json"}
    
    # UPGRADED PAYLOAD: Clean production content list wrapping dictionary array
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        
        # EXPLICIT GUARDRAIL: Safely capture raw non-JSON outputs before they cause a parsing crash
        if res.status_code != 200:
            return f"Gemini server dropped request with status code {res.status_code}. Raw output body: {res.text[:150]}"
            
        res_json = res.json()
        
        if 'candidates' in res_json and len(res_json['candidates']) > 0:
            candidate = res_json['candidates'][0]
            if 'content' in candidate and 'parts' in candidate['content'] and len(candidate['content']['parts']) > 0:
                return candidate['content']['parts'][0]['text']
        
        return f"AI system returned unexpected response data matrix structure: {str(res_json)[:150]}"
    except Exception as e:
        return f"AI processing system pipeline parsing exception occurred: {str(e)}"

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



# Fresh build trigger verification