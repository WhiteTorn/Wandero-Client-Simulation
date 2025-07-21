"""Node functions for the client graph"""

import random
import time
from typing import Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from client_state import ClientState
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.7
)

def initial_inquiry_node(state: ClientState) -> Dict[str, Any]:
    """Node 1: Generate initial inquiry"""
    print("🔄 Node: Generating initial inquiry...")
    
    prompt = f"""You are {state['persona_name']}, a {state['persona_type']}.
Write a natural initial email inquiring about a family trip to Chile.
Be conversational and mention you're interested but DON'T include:
- Exact number of people
- Specific travel dates  
- Children's ages
- Budget

Keep it 2-3 paragraphs, friendly and excited about the trip."""

    response = llm.invoke(prompt).content
    
    # Add typo for realism
    if "Chile" in response:
        response = response.replace("Chile", "Chlie", 1)
    
    return {
        "messages": [{"role": "client", "content": response, "turn": 1}],
        "phase": "awaiting_wandero_response",
        "turn_count": state["turn_count"] + 1,
        "provided_info": {
            "inquiry_sent": True,
            "travelers_count": False,
            "dates": False,
            "ages": False,
            "budget": False,
            "special_needs": False
        }
    }

def analyze_wandero_response_node(state: ClientState) -> Dict[str, Any]:
    """Node 2: Analyze what Wandero is asking for"""
    print("🔄 Node: Analyzing Wandero's response...")
    
    # Find last Wandero message
    wandero_message = ""
    for msg in reversed(state["messages"]):
        if msg["role"] == "wandero":
            wandero_message = msg["content"].lower()
            break
    
    # Extract what Wandero is requesting
    requests = []
    if "number of travelers" in wandero_message:
        requests.append("travelers")
    if "dates" in wandero_message:
        requests.append("dates")
    if "budget" in wandero_message:
        requests.append("budget")
    if "ages" in wandero_message:
        requests.append("ages")
    
    # Determine next phase based on content
    next_phase = state["phase"]
    if requests and not state["provided_info"]["travelers_count"]:
        next_phase = "providing_details"
    elif "itinerary" in wandero_message and "cost" in wandero_message:
        next_phase = "reviewing_proposal"
    elif "invoice" in wandero_message or "payment" in wandero_message:
        next_phase = "confirming_booking"
    
    return {
        "wandero_requests": requests,
        "phase": next_phase,
        "turn_count": state["turn_count"] + 1
    }

def provide_details_node(state: ClientState) -> Dict[str, Any]:
    """Node 3: Provide requested details (but forget something)"""
    print("🔄 Node: Providing details to Wandero...")
    
    # Decide what to forget
    should_forget_ages = not state["provided_info"]["ages"] and random.random() < 0.7
    should_forget_allergy = random.random() < 0.5
    
    prompt = f"""You are {state['persona_name']}.
Wandero asked for travel details. Provide:
- We are 4 people (2 adults, 2 children) 
- Travel dates: July 15-22, 2024
- Budget: $4000-6000 total
- Looking for family-friendly activities

{"BUT DON'T mention the children's ages yet." if should_forget_ages else "Mention children are 12 and 8."}
{"Also forget to mention your son Jack has a nut allergy." if should_forget_allergy else ""}

Be natural and conversational. Show enthusiasm."""

    response = llm.invoke(prompt).content
    
    # Update what we've provided
    updated_info = state["provided_info"].copy()
    updated_info["travelers_count"] = True
    updated_info["dates"] = True
    updated_info["budget"] = True
    if not should_forget_ages:
        updated_info["ages"] = True
    
    # Track what we forgot
    forgotten = []
    if should_forget_ages:
        forgotten.append("ages")
    if should_forget_allergy:
        forgotten.append("allergy")
    
    return {
        "messages": [{"role": "client", "content": response, "turn": state["turn_count"]}],
        "phase": "awaiting_wandero_response",
        "provided_info": updated_info,
        "needs_correction": len(forgotten) > 0,
        "forgotten_details": forgotten,
        "turn_count": state["turn_count"] + 1
    }

def send_correction_node(state: ClientState) -> Dict[str, Any]:
    """Node 4: Send a correction email"""
    print("🔄 Node: Sending correction email...")
    
    corrections = []
    if "ages" in state["forgotten_details"] and not state["provided_info"]["ages"]:
        corrections.append("the children are 12 and 8 years old")
    if "allergy" in state["forgotten_details"]:
        corrections.append("my son Jack has a severe nut allergy")
    
    if not corrections:
        return {"needs_correction": False}
    
    prompt = f"""You are {state['persona_name']}.
Write a brief follow-up email saying you forgot to mention: {corrections[0]}
Start with "Oh, I just realized..." or "Sorry, I forgot to mention..."
Keep it short and natural."""

    response = llm.invoke(prompt).content
    
    # Update provided info
    updated_info = state["provided_info"].copy()
    if "ages" in state["forgotten_details"]:
        updated_info["ages"] = True
    if "allergy" in state["forgotten_details"]:
        updated_info["special_needs"] = True
    
    return {
        "messages": [
            {"role": "system", "content": "[5 minutes later]"},
            {"role": "client", "content": response, "turn": state["turn_count"]}
        ],
        "phase": "awaiting_wandero_response",
        "needs_correction": False,
        "provided_info": updated_info,
        "turn_count": state["turn_count"] + 1
    }

def review_proposal_node(state: ClientState) -> Dict[str, Any]:
    """Node 5: Review and respond to proposal"""
    print("🔄 Node: Reviewing Wandero's proposal...")
    
    prompt = f"""You are {state['persona_name']}.
Wandero sent you a tour proposal. Write an enthusiastic acceptance.
Mention you're excited about specific aspects like:
- The Atacama Desert
- Family-friendly hotels
- The itinerary

End by asking them to send the invoice."""

    response = llm.invoke(prompt).content
    
    return {
        "messages": [{"role": "client", "content": response, "turn": state["turn_count"]}],
        "phase": "confirming_booking",
        "turn_count": state["turn_count"] + 1
    }

def end_conversation_node(state: ClientState) -> Dict[str, Any]:
    """Node 6: End the conversation"""
    print("✅ Conversation completed!")
    return {"phase": "conversation_ended"}