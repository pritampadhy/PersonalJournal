#!/usr/bin/env python3
"""
Multi-Agent Reasoning & Scoring System Orchestrator.

This script manages a 3-agent workflow using the official Google GenAI Core SDK (`google-genai`):
1. Researcher Agent: Formulates initial thesis & key evidence.
2. Devil's Advocate Agent: Stress-tests assumptions and provides counter-arguments.
3. Balancer & Scorer Agent: Evaluates both perspectives with a 1-10 scoring matrix and provides a verdict.

Outputs are written to `common.md` with token-conscious summaries.
"""

import os
import sys
import datetime
import warnings
import io

# Enforce UTF-8 output encoding for terminals with ASCII/POSIX default encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Suppress minor version warnings for clean CLI output
warnings.filterwarnings("ignore")

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Error: Required 'google-genai' package not found.")
    print("Please install it using: pip install google-genai")
    sys.exit(1)

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
COMMON_FILE = os.path.join(PROJECT_DIR, "common.md")

def init_common_ledger():
    if not os.path.exists(COMMON_FILE):
        with open(COMMON_FILE, "w", encoding="utf-8") as f:
            f.write("# 🌐 Shared Global Ledger (`common.md`)\n")
            f.write("> Multi-Agent Reasoning, Adversarial Critique, and Scoring Ledger.\n\n")

def append_round(icon: str, round_num: int, agent_name: str, topic: str, content: str):
    init_common_ledger()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"""---
## {icon} Round {round_num}: {agent_name}
**Topic:** `{topic}`  
**Timestamp:** *{timestamp}*  

{content.strip()}

"""
    with open(COMMON_FILE, "a", encoding="utf-8") as f:
        f.write(entry)
    print(f"✅ Appended Round {round_num} ({agent_name}) to {COMMON_FILE}")

def run_researcher(client, model_name, topic):
    print("🤖 Agent 1 (Researcher) is thinking...")
    sys_instruction = (
        "You are a Researcher Subagent. Your goal is to conduct structured research and propose an initial thesis on the topic.\n"
        "Strict Token Control: Output MUST be highly concise markdown. Use bullet points and minimal words. Do not include conversational filler."
    )
    prompt = f"Topic: {topic}\n\nProvide your structured research and thesis."
    
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=sys_instruction,
            temperature=0.2,
        )
    )
    return response.text

def run_devils_advocate(client, model_name, topic, researcher_output):
    print("🤖 Agent 2 (Devil's Advocate) is thinking...")
    sys_instruction = (
        "You are the Devil's Advocate Subagent. Your goal is to use reasoning techniques to stress-test assumptions, highlight risks, and present counter-arguments to the Researcher's thesis.\n"
        "Strict Token Control: Output MUST be highly concise markdown. Use bullet points and minimal words. Do not include conversational filler."
    )
    prompt = f"Topic: {topic}\n\nResearcher's Thesis:\n{researcher_output}\n\nProvide your counter-arguments and risk highlights."
    
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=sys_instruction,
            temperature=0.2,
        )
    )
    return response.text

def run_scorer(client, model_name, topic, researcher_output, advocate_output):
    print("🤖 Agent 3 (Scorer & Balancer) is thinking...")
    sys_instruction = (
        "You are the Scorer & Balancer Subagent. Evaluate both perspectives using a quantitative scoring matrix (Logic, Evidence, Feasibility, Risk) and formulate a balanced consensus.\n"
        "Strict Token Control: Output MUST be a concise JSON or Markdown Table followed by a short consensus paragraph."
    )
    prompt = (
        f"Topic: {topic}\n\n"
        f"Researcher's Thesis:\n{researcher_output}\n\n"
        f"Devil's Advocate Critique:\n{advocate_output}\n\n"
        "Provide the scoring matrix and final consensus."
    )
    
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=sys_instruction,
            temperature=0.2,
        )
    )
    return response.text

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 orchestrator.py '<Topic or Question>'")
        sys.exit(1)

    topic = sys.argv[1]
    print(f"\n🚀 Initiating Multi-Agent Debate & Scoring Workflow (Google GenAI Core SDK)")
    print(f"📌 Topic: {topic}")
    print(f"📁 Ledger: {COMMON_FILE}\n")
    
    raw_key = os.environ.get("GOOGLE_API_KEY")
    if not raw_key:
        print("Error: GOOGLE_API_KEY environment variable is not set.")
        print("Please set it using: export GOOGLE_API_KEY='your-api-key'")
        sys.exit(1)

    # Strip whitespace, standard quotes, and unicode smart quotes (“ ” ‘ ’)
    api_key = raw_key.strip().strip("'\"“”‘’")
    # Remove any non-ASCII characters from the API key
    api_key = "".join(c for c in api_key if ord(c) < 128)

    # Initialize the Google GenAI Client directly (uses HTTP REST, avoiding gRPC metadata bugs)
    client = genai.Client(api_key=api_key)
    
    # Model selection: standard fast & powerful models like gemini-3.6-flash
    model_name = "gemini-3.6-flash"

    try:
        # Agent 1: Researcher
        res_output = run_researcher(client, model_name, topic)
        append_round("🔍", 1, "Researcher", topic, res_output)
        
        # Agent 2: Devil's Advocate (context slice: topic + researcher output)
        adv_output = run_devils_advocate(client, model_name, topic, res_output)
        append_round("😈", 2, "Devil's Advocate", topic, adv_output)
        
        # Agent 3: Scorer & Balancer (context slice: topic + researcher output + advocate output)
        score_output = run_scorer(client, model_name, topic, res_output, adv_output)
        append_round("⚖️", 3, "Scorer & Balancer", topic, score_output)

        print("\n🎉 Workflow complete! Results cleanly logged in common.md.")
    except Exception as e:
        print(f"\n❌ Error during multi-agent execution: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
