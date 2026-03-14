# 🏥 MediQ: The Self-Learning Agentic Healthcare Framework

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)
![Groq](https://img.shields.io/badge/AI-Groq%20Llama--3-orange)
![FastMCP](https://img.shields.io/badge/Integration-Claude%20MCP-purple)

**Curing the queue, one query at a time.** MediQ transforms static, legacy medical databases into lightning-fast, interconnected reasoning engines using Agentic AI, Knowledge Graphs, and the Model Context Protocol (MCP).

---

## 💡 1. Introduction & Motivation

### The Problem
Hospitals in high-population regions are paralyzed by massive waiting queues and overwhelming amounts of Medical Big Data. Doctors and administrative staff spend entirely too much time querying slow, legacy relational databases instead of treating patients. Traditional databases are static; they fetch data, but they don't *learn* from it.

### The Solution
MediQ was built to act as an intelligent intermediary layer between healthcare staff and legacy databases. Operating on a **"Fetch Once, Learn Forever"** architecture, MediQ intercepts standard queries, dynamically extracts semantic relationships to build an in-memory Knowledge Graph, and intelligently bypasses the legacy database on subsequent queries. This results in sub-second data retrieval and drastically reduced server loads.

---

## ⚙️ 2. Tech Stack & Architecture

### Tech Stack
* **Backend:** Python, Flask, FastMCP
* **Database & Graph Store:** MongoDB, NetworkX
* **AI & Orchestration:** Groq API (Llama-3.1-8b-instant for routing, Llama-3.3-70b-versatile for extraction)
* **Frontend UI:** Vanilla JS, Tailwind CSS, Vis.js (Live Physics Graph), Chart.js (Live Telemetry)

### How It Works: The "Circuit Breaker" Architecture
MediQ operates via a smart Agentic Orchestrator with two main data flow paths:

1. **Path A (The Database Miss):** The user asks a new question. The AI checks the Knowledge Graph, finds it empty, and utilizes **Autonomous Tool Chaining** to hit the MongoDB database (via Port 5090). A background Extractor LLM secretly reads this JSON data, distills it into relational triplets `[Subject, Relationship, Object]`, and writes it to the visual Graph.
2. **Path B (The Graph Hit - The Circuit Breaker):** The user asks a follow-up question. The Orchestrator scans the Graph, detects the context, and instantly triggers the "Circuit Breaker." It forcibly hides the database tools from the LLM, forcing a sub-second response generated entirely from the in-memory Graph. 

---

## 🚀 3. Setup & Installation Guide

Follow these steps to run the MediQ MVP locally on your machine.

### Prerequisites
* Docker Desktop installed and running.
* Python 3.10+ installed.
* Claude Desktop App installed (for Enterprise MCP integration).
* A free [Groq API Key](https://console.groq.com/keys).

### Step 1: Clone the Repository
```bash
git clone https://github.com/gerardjoshi/mediq
cd mediq
```

# MediQ Setup & Deployment Guide

---

## Step 2: Start MongoDB via Docker

Spin up a local MongoDB instance to act as the legacy hospital database. Use the import.js on a MongoDb Database PLayground to directly import into Your mongo instance

```bash
docker run -d -p 27017:27017 --name mediq-mongo mongo:latest
```

> **Note:** Ensure your Maven Analytics healthcare dataset is imported into a database named `healthcare_db` within this Mongo instance. The import.js does this on its own

---

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Step 4: Configure API Keys

Open `agent_server.py` and replace the placeholder Groq API key on **line 17** with your actual key:

```python
client = Groq(api_key="gsk_your_actual_key_here")
```

---

## Step 5: Boot the Legacy Database API

Open a terminal and start the Flask database server (runs on **Port 5090** to avoid macOS AirPlay conflicts):

```bash
python3 server.py
```

---

## Step 6: Boot the Agentic UI (MediQ Hub)

Open a **second terminal window** and start the Orchestrator and UI:

```bash
python3 agent_server.py
```

Access the clinical dashboard at: [http://localhost:8000/](http://localhost:8000/)

---

## Step 7: Configure Claude Desktop (MCP Server)

To test the enterprise deployment, connect MediQ to Claude Desktop.

1. Open **Claude Desktop**.
2. Navigate to **Settings → Developer → Edit Config**.
3. Replace the contents with the following JSON — ensure the paths point to your exact local directories and Python executable:

```json
{
  "mcpServers": {
    "mediq-mcp": {
      "command": "/opt/homebrew/bin/python3", // or the actual path to your system's python bin
      "args": [
        "/Absolute/Path/To/Your/MediQ/mcp_server.py"
      ]
    }
  }
}
```

4. **Save** the file and **restart** Claude Desktop.
5. Click the **🔨 Hammer** icon in the chat bar to verify the MediQ tools are loaded.

---

## 🔮 Enterprise Roadmap: Setting up Kafka

While the MVP uses synchronous, in-memory triplet extraction, scaling MediQ to handle millions of concurrent hospital patients requires decoupling the Knowledge Extractor from the main Agentic loop.

### Future Architecture Implementation

| Step | Component | Description |
|------|-----------|-------------|
| 1 | **Message Broker** | Deploy Apache Kafka via Docker Compose alongside Neo4j |
| 2 | **Producer Logic** | On a "Graph Miss", `agent_server.py` publishes raw JSON to a Kafka topic (e.g. `topic.knowledge.extraction`) instead of processing immediately |
| 3 | **Consumer Workers** | A dedicated pool of Python worker nodes subscribes to the topic, using the heavy 70B LLM to extract triplets asynchronously |
| 4 | **Graph Persistence** | Workers write resulting triplets directly to a persistent Neo4j enterprise database — ensuring **zero UI blocking** and massive horizontal scalability |

---

## 👨‍💻 Credits

Built with ☕ and late-night debugging for the hackathon.

**Developed by:**

- **Gerard & Rithik**
- National Institute of Technology Tiruchirappalli (**NITT**)
