"""Client simulator using LangGraph and Google Gemini"""

import os
import time
import random
from typing import TypedDict, List, Dict
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI

from personas import PERSONAS

load_dotenv()

# Initialize Gemini
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.7
)

class ClientState(TypedDict):
    """State for the client conversation"""
    messages: List[Dict[str, str]]
    persona: Dict
    current_phase: str
    pending_corrections: List[str]
    mentioned_details: List[str]
    conversation_count: int
    sender_name: str
    travel_dates: str

def safe_llm_invoke(prompt: str, delay_seconds: int = 2) -> str:
    """Safely invoke LLM with error handling and delays"""
    try:
        print(f"🤖 Making LLM request... (waiting {delay_seconds}s first)")
        time.sleep(delay_seconds)  # Always wait before making request
        
        response = llm.invoke(prompt).content
        
        print(f"✅ LLM request successful")
        time.sleep(1)  # Additional small delay after successful request
        
        return response
    except Exception as e:
        print(f"❌ LLM API Error: {e}")
        if "429" in str(e) or "quota" in str(e).lower():
            print("⏰ Rate limit hit, waiting longer...")
            time.sleep(30)  # Wait 30 seconds for rate limit
            
            # Try once more
            try:
                response = llm.invoke(prompt).content
                print("✅ Retry successful")
                return response
            except Exception as retry_error:
                print(f"❌ Retry failed: {retry_error}")
                # Return a fallback response
                return "I'd like to proceed with planning our family trip to Chile. Please let me know what information you need."
        
        # For other errors, return fallback
        return "Thank you for your response. I'm interested in planning our trip."

def create_initial_inquiry(state: ClientState) -> ClientState:
    """Generate the initial inquiry email"""
    persona = state["persona"]
    
    prompt = f"""You are {persona['name']}, a {persona['type']}.
Your traits: {', '.join(persona['traits'])}
Your concerns: {', '.join(persona['concerns'][:2])}  # Don't mention all concerns initially

Write a natural initial email inquiring about a family trip to Chile.
Be {persona['communication_style']}.
Mention you want to travel but 'forget' to include some important details like:
- Exact number of people
- Specific dates
- Children's ages

Keep it conversational and realistic. 2-3 paragraphs max. """

    response = safe_llm_invoke(prompt, delay_seconds=3)
    
    # Add some typos for realism
    if random.random() < 0.3:
        response = introduce_typo(response)
    
    return {
        **state,
        "messages": state["messages"] + [{"role": "client", "content": response}],
        "current_phase": "inquiry_sent",
        "mentioned_details": ["chile", "family"],
        "conversation_count": state["conversation_count"] + 1
    }

def analyze_wandero_response(state: ClientState) -> ClientState:
    """Analyze what Wandero is asking for"""
    last_wandero_message = None
    for msg in reversed(state["messages"]):
        if msg["role"] == "wandero":
            last_wandero_message = msg["content"]
            break
    
    if not last_wandero_message:
        return state
    
    # Determine what info is being requested
    requested_info = []
    if "number of travelers" in last_wandero_message.lower():
        requested_info.append("travelers")
    if "dates" in last_wandero_message.lower():
        requested_info.append("dates")
    if "budget" in last_wandero_message.lower():
        requested_info.append("budget")
    
    return {
        **state,
        "current_phase": "analyzing_request",
        "pending_corrections": determine_corrections(state, requested_info)
    }

def provide_details(state: ClientState) -> ClientState:
    """Respond with requested details (but maybe forget something)"""
    persona = state["persona"]
    last_wandero_msg = state["messages"][-1]["content"]
    
    # Determine what to include/forget
    should_forget_something = random.random() < 0.6  # 60% chance to forget something
    
    prompt = f"""You are {persona['name']} responding to this travel agency email:
"{last_wandero_msg}"

Provide the requested information but in a natural, conversational way.
Include:
- You're {len(persona['family']['children']) + 2} people total
- Mention travel dates: {persona['travel_dates']['preferred']}
- Your budget is {persona['budget_range']}

{'BUT FORGET to mention one important detail like children ages or a food allergy. Youll remember this later.' if should_forget_something else 'Include all details.'}

Be {persona['communication_style']}. Keep it natural and conversational."""

    response = safe_llm_invoke(prompt, delay_seconds=3)
    
    return {
        **state,
        "messages": state["messages"] + [{"role": "client", "content": response}],
        "current_phase": "details_provided",
        "mentioned_details": state["mentioned_details"] + ["travelers", "dates", "budget"],
        "conversation_count": state["conversation_count"] + 1
    }

def send_correction(state: ClientState) -> ClientState:
    """Send a follow-up correction email"""
    persona = state["persona"]
    
    # Pick what we "forgot"
    forgotten_items = []
    if "ages" not in state["mentioned_details"]:
        forgotten_items.append(f"children are {persona['family']['children'][0]['age']} and {persona['family']['children'][1]['age']} years old")
    if "allergy" not in state["mentioned_details"]:
        forgotten_items.append(f"{persona['family']['children'][1]['name']} has a severe nut allergy")
    
    if not forgotten_items:
        return state
    
    prompt = f"""You are {persona['name']}. Write a short follow-up email where you just remembered something important.
    
Mention that you forgot to tell them: {forgotten_items[0]}

Start with something like "Oh, I just realized I forgot to mention..." or "Sorry, one more thing..."
Keep it brief and {persona['communication_style']}."""

    response = safe_llm_invoke(prompt, delay_seconds = 3)
    
    # Add realistic delay marker
    time_delay = f"[Sent {random.randint(2, 15)} minutes after previous email]"
    
    return {
        **state,
        "messages": state["messages"] + [
            {"role": "system", "content": time_delay},
            {"role": "client", "content": response}
        ],
        "current_phase": "correction_sent",
        "mentioned_details": state["mentioned_details"] + ["ages", "allergy"],
        "conversation_count": state["conversation_count"] + 1
    }

def review_proposal(state: ClientState) -> ClientState:
    """Review and respond to Wandero's proposal"""
    persona = state["persona"]
    last_message = state["messages"][-1]["content"]
    
    # Randomly decide whether to accept, ask questions, or request changes
    action = random.choice(["accept", "question", "modify"])
    
    if action == "accept":
        prompt = f"""You are {persona['name']}. The travel agency sent you this proposal:
"{last_message}"

You're happy with it! Write an enthusiastic confirmation email.
Be {persona['communication_style']}. Express excitement about specific parts of the trip."""
    
    elif action == "question":
        prompt = f"""You are {persona['name']}. Ask 1-2 specific questions about the proposal.
Maybe about: activities for kids, meal options, weather, or safety measures.
Be {persona['communication_style']}."""
    
    else:  # modify
        prompt = f"""You are {persona['name']}. Request one small change to the proposal.
Maybe: different dates, hotel upgrade, or adding an activity.
Be polite and {persona['communication_style']}."""
    
    response = safe_llm_invoke(prompt, delay_seconds=3)
    
    return {
        **state,
        "messages": state["messages"] + [{"role": "client", "content": response}],
        "current_phase": "proposal_reviewed",
        "conversation_count": state["conversation_count"] + 1
    }

def determine_next_action(state: ClientState) -> str:
    """Decide what the client should do next"""
    phase = state["current_phase"]
    conversation_count = state["conversation_count"]
    
    if phase == "inquiry_sent":
        return "wait_for_response"
    elif phase == "analyzing_request":
        return "provide_details"
    elif phase == "details_provided" and len(state["pending_corrections"]) > 0:
        return "send_correction"
    elif "proposal" in state["messages"][-1]["content"].lower() and phase != "proposal_reviewed":
        return "review_proposal"
    elif phase == "proposal_reviewed" or conversation_count > 6:
        return "end_conversation"
    else:
        return "wait_for_response"

def introduce_typo(text: str) -> str:
    """Introduce a realistic typo"""
    typos = [
        ("the", "teh"),
        ("and", "adn"),
        ("family", "familly"),
        ("would", "woudl"),
        ("Chile", "Chlie")
    ]
    
    typo = random.choice(typos)
    return text.replace(typo[0], typo[1], 1)

def determine_corrections(state: ClientState, requested_info: List[str]) -> List[str]:
    """Determine what corrections to send later"""
    corrections = []
    if "ages" not in state["mentioned_details"]:
        corrections.append("children_ages")
    if "allergy" not in state["mentioned_details"] and random.random() < 0.7:
        corrections.append("food_allergy")
    return corrections

def create_client_graph(persona_type: str = "worried_parent"):
    """Create the client state machine"""
    
    # Initialize workflow
    workflow = StateGraph(ClientState)
    
    # Add nodes
    workflow.add_node("initial_inquiry", create_initial_inquiry)
    workflow.add_node("analyze_response", analyze_wandero_response)
    workflow.add_node("provide_details", provide_details)
    workflow.add_node("send_correction", send_correction)
    workflow.add_node("review_proposal", review_proposal)
    
    # Set entry point
    workflow.set_entry_point("initial_inquiry")
    
    # Add conditional edges instead of fixed edges
    workflow.add_conditional_edges(
        "initial_inquiry",
        lambda state: "end" if state["conversation_count"] > 0 else "analyze_response",
        {
            "analyze_response": "analyze_response",
            "end": END
        }
    )
    
    workflow.add_conditional_edges(
        "analyze_response", 
        determine_next_action,
        {
            "provide_details": "provide_details",
            "end_conversation": END,
            "wait_for_response": END
        }
    )
    
    workflow.add_conditional_edges(
        "provide_details",
        determine_next_action, 
        {
            "send_correction": "send_correction",
            "end_conversation": END,
            "wait_for_response": END
        }
    )
    
    workflow.add_conditional_edges(
        "send_correction",
        determine_next_action,
        {
            "provide_details": "provide_details", 
            "end_conversation": END,
            "wait_for_response": END
        }
    )
    
    workflow.add_edge("review_proposal", END)
    
    # Compile
    return workflow.compile()

def initialize_client_state(persona_type: str) -> ClientState:
    """Initialize the client state with persona"""
    persona = PERSONAS[persona_type]
    
    return {
        "messages": [],
        "persona": persona,
        "current_phase": "not_started",
        "pending_corrections": [],
        "mentioned_details": [],
        "conversation_count": 0,
        "sender_name": persona["name"],
        "travel_dates": persona["travel_dates"]["preferred"]
    }