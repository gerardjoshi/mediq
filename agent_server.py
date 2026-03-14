import os
import json
import time
import uuid
import requests
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from groq import Groq

# Import our custom modules
from graph_store import KnowledgeGraph
from extractor import extract_knowledge_triplets

app = Flask(__name__)

# IMPORTANT: Put your actual Groq API Key here!
client = Groq(api_key="lol_bro_u_thought_i_would_expose_my_api_key_ahahaha") 

DB_BASE_URL = "http://localhost:5090/api"

# ==========================================
# 1. SESSION MANAGEMENT (New!)
# ==========================================
sessions = {}

def create_session(name=None):
    """Creates a completely isolated session with its own memory, graph, and telemetry."""
    sid = str(uuid.uuid4())
    sessions[sid] = {
        "id": sid,
        "name": name or f"Clinical Session {datetime.now().strftime('%H:%M')}",
        "graph": KnowledgeGraph(),
        "memory": [],
        "metrics": {
            "graph_hits": 0, 
            "graph_misses": 0, 
            "total_hit_time": 0.0, 
            "total_miss_time": 0.0
        }
    }
    return sid

# Initialize the very first session when the server starts
default_sid = create_session("Initial Session")

def get_current_session():
    """Safely retrieves the session requested by the UI, or falls back to default."""
    sid = request.args.get('session_id') if request.method == 'GET' else request.json.get('session_id')
    if not sid or sid not in sessions:
        return sessions[default_sid]
    return sessions[sid]

# ==========================================
# 2. TOOL DEFINITIONS (The Agent's Toolkit)
# ==========================================
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_patient_history",
            "description": "Retrieve a chronological timeline of a specific patient's medical history.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_id": {"type": "string", "description": "The exact UUID of the patient."}
                },
                "required": ["patient_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_procedures",
            "description": "Retrieve records of medical procedures or surgeries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_id": {"type": "string", "description": "The exact UUID of the patient."}
                },
                "required": ["patient_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_patients_by_name",
            "description": "Find a patient's UUID using their first or last name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "first_name": {"type": "string", "description": "Patient's first name"},
                    "last_name": {"type": "string", "description": "Patient's last name"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_patient_count_by_factor",
            "description": "Get the total count of unique patients based on a specific clinical factor or diagnosis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "factor_value": {"type": "string", "description": "The clinical value to search for (e.g., 'Viral sinusitis')"}
                },
                "required": ["factor_value"]
            }
        }
    }
]

# ==========================================
# 3. KNOWLEDGE EXTRACTOR ROUTING
# ==========================================
def fetch_db_and_learn(endpoint: str, params: dict, current_graph):
    """Hits the external DB, extracts triplets, updates the CURRENT session's Graph."""
    print(f"\n[System] DB Call: {endpoint} {params}")
    try:
        response = requests.get(f"{DB_BASE_URL}{endpoint}", params=params)
        response.raise_for_status()
        data = response.json()
        
        # Pass to extractor if we have valid data
        if data and not (isinstance(data, dict) and "error" in data):
            triplets = extract_knowledge_triplets(data)
            if triplets: 
                current_graph.add_triplets(triplets)
                
        return data
    except Exception as e:
        return {"error": str(e)}

# ==========================================
# 4. API ENDPOINTS (UI & Telemetry)
# ==========================================
# ==========================================
# FRONTEND ROUTE
# ==========================================
@app.route('/')
def index():
    """Serves the main MediQ dashboard."""
    return render_template('index.html')
@app.route('/api/sessions', methods=['GET'])
def list_sessions():
    """Returns all active sessions for the UI sidebar."""
    return jsonify([{"id": s["id"], "name": s["name"]} for s in sessions.values()])

@app.route('/api/sessions', methods=['POST'])
def new_session():
    """Spins up a brand new session."""
    sid = create_session()
    return jsonify({"id": sid, "name": sessions[sid]["name"]})

@app.route('/api/history', methods=['GET'])
def get_history():
    """Returns the clean chat memory for the active session."""
    return jsonify(get_current_session()["memory"])

@app.route('/api/graph', methods=['GET'])
def get_graph():
    """Returns the visual node/edge data for the active session's graph."""
    return jsonify(get_current_session()["graph"].get_vis_data())

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Calculates live latency metrics for the active session."""
    metrics = get_current_session()["metrics"]
    avg_hit = metrics["total_hit_time"] / metrics["graph_hits"] if metrics["graph_hits"] > 0 else 0
    avg_miss = metrics["total_miss_time"] / metrics["graph_misses"] if metrics["graph_misses"] > 0 else 0
    return jsonify({
        "hits": metrics["graph_hits"], 
        "misses": metrics["graph_misses"],
        "avg_hit_time": round(avg_hit, 2), 
        "avg_miss_time": round(avg_miss, 2)
    })

# ==========================================
# 5. THE MAIN AGENTIC RAG LOOP
# ==========================================
@app.route('/api/chat', methods=['POST'])
def chat():
    start_time = time.time()
    user_msg = request.json.get('message')
    session = get_current_session()
    
    # --- CIRCUIT BREAKER: Search Graph First ---
    graph_context = session["graph"].search_graph(user_msg)
    
    graph_hit = False
    if len(graph_context) > 0:
        first_item = str(graph_context[0]).lower()
        if "empty" not in first_item and "no matching" not in first_item:
            graph_hit = True
            
    # --- DYNAMIC ROUTING ---
    if graph_hit:
        print(f"\n[System] ⚡ GRAPH HIT! Found context. Bypassing database.")
        system_prompt = (
            "You are MediQ, a fast AI Agent. You MUST answer the user's question using ONLY the provided Knowledge Graph context.\n"
            f"KNOWLEDGE GRAPH CONTEXT:\n{json.dumps(graph_context)}\n\n"
            "Keep your answer clinical and concise. Do not mention that you are reading from a graph."
        )
        active_tools = None # HIDE TOOLS to force instant response
        source_badge = "⚡ [Fast Graph Response] "
    else:
        print("\n[System] 🔴 GRAPH MISS. Enabling tools.")
        system_prompt = (
            "You are MediQ, a strict Data Routing Agent. The Knowledge Graph is empty for this query.\n"
            "You MUST call the appropriate database tool to fetch the data. Do not guess."
        )
        active_tools = tools # PROVIDE TOOLS
        source_badge = "🔍 [Database & Extractor Response] "

    # --- CLEAN MEMORY ASSEMBLY ---
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(session["memory"])
    messages.append({"role": "user", "content": user_msg})

    api_kwargs = {"model": "llama-3.1-8b-instant", "messages": messages}
    if active_tools:
        api_kwargs["tools"] = active_tools
        api_kwargs["tool_choice"] = "auto"

    # --- INITIAL LLM CALL ---
    response = client.chat.completions.create(**api_kwargs)
    response_message = response.choices[0].message

    # --- TOOL EXECUTION LOOP ---
    if getattr(response_message, "tool_calls", None):
        messages.append({
            "role": "assistant",
            "tool_calls": [{"id": t.id, "type": "function", "function": {"name": t.function.name, "arguments": t.function.arguments}} for t in response_message.tool_calls]
        })
        
        for tool_call in response_message.tool_calls:
            args = json.loads(tool_call.function.arguments)
            tool_name = tool_call.function.name
            
            # Route to the correct API, passing the current session's graph
            if tool_name == "get_patient_history":
                result = fetch_db_and_learn("/patient/history", {"patientId": args.get("patient_id")}, session["graph"])
            elif tool_name == "get_procedures":
                result = fetch_db_and_learn("/procedures", {"patientId": args.get("patient_id")}, session["graph"])
            elif tool_name == "search_patients_by_name":
                result = fetch_db_and_learn("/patients/search", {"firstName": args.get("first_name"), "lastName": args.get("last_name")}, session["graph"])
            elif tool_name == "get_patient_count_by_factor":
                result = fetch_db_and_learn("/analytics/patient_count", {"factorValue": args.get("factor_value")}, session["graph"])
            else:
                result = {"error": "Tool not implemented"}
                
            # Token Limit Protection (Truncation)
            result_str = json.dumps(result)
            if len(result_str) > 3000:
                result_str = result_str[:3000] + "... [Data Truncated. The Graph has been updated!]"

            messages.append({"role": "tool", "tool_call_id": tool_call.id, "name": tool_name, "content": result_str})
            
        # Final LLM call after the tools finish
        final_response = client.chat.completions.create(model="llama-3.1-8b-instant", messages=messages)
        reply = source_badge + final_response.choices[0].message.content
        
        # Save ONLY the text to long-term memory
        session["memory"].append({"role": "user", "content": user_msg})
        session["memory"].append({"role": "assistant", "content": reply})
        
        # Log telemetry
        session["metrics"]["graph_misses"] += 1
        session["metrics"]["total_miss_time"] += (time.time() - start_time)
        return jsonify({"reply": reply})

    # --- NO TOOLS NEEDED (Graph Hit) ---
    reply = source_badge + response_message.content
    session["memory"].append({"role": "user", "content": user_msg})
    session["memory"].append({"role": "assistant", "content": reply})
    
    # Log telemetry 
    session["metrics"]["graph_hits"] += 1
    session["metrics"]["total_hit_time"] += (time.time() - start_time)
    return jsonify({"reply": reply})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
