import requests 
import json
print("AI-OS Assistant is starting...")
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3.6:27B"
SYSTEM_PROMPT = """You are AI-OS, Ana's personal AI assistant."""
conversation_history = []
MEMORY_FILE = "memory.json"
PROFILE_FILE = "profile.json" 
def save_profile(profile):
     with open(PROFILE_FILE, "w") as file:
          json.dump(profile, file)

def load_profile():
     try:
          with open(PROFILE_FILE, "r") as file:
               return json.load(file)
     except FileNotFoundError:
          return {}

def save_memory():
     with open(MEMORY_FILE, "w") as file:
          json.dump(conversation_history, file)

def load_memory():
     try:
          with open(MEMORY_FILE, "r") as file:
               return json.load(file)
     except FileNotFoundError:
          return []     
conversation_history = load_memory()
profile = load_profile()
def ask_qwen(prompt):
     conversation_history.append("User: " + prompt)
     data = { 
        "model": MODEL,
     "prompt": SYSTEM_PROMPT + "\n\nProfile: " + json.dumps(profile) + "\n\n" + "\n".join(conversation_history),
        "stream": False 
    }
     response = requests.post(OLLAMA_URL, json=data)
     result = response.json()
     conversation_history.append("AI-OS: " + result["response"])
     save_memory()
     return result["response"]
name = input("what is your name?")

print("hello,", name)

while True:
     question = input("You: ")
     if question.lower() in ["exit", "quit", "bye"]:
          print("AI-OS: Goodbye!")
          break
     if question == "Remember that I live in Serbia.":
          profile["country"] = "Serbia"
          save_profile(profile)
     response = ask_qwen(question)
     print("AI-OS:", response)

