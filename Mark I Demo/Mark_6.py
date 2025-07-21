"""Multi Persona Stress Testing System."""

from typing import TypedDict, List, Dict, Literal, Annotated, Optional, Any, Tuple
from datetime import datetime, timedelta
import operator
import os
import re
import random
import json
import csv
import html
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading
from dataclasses import dataclass
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from IPython.display import Image, display
from time import sleep
from langgraph.checkpoint.memory import MemorySaver 
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from collections import Counter

# Initialize components
load_dotenv()
memory = MemorySaver()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.7
)

# Type definitions
class ConversationMetadata(TypedDict):
    thread_id: str
    started_at: str
    last_updated: str
    email_count: int
    current_topic: str

class ClientState(TypedDict):
    """Enhanced client state with memory and metadata"""
    messages: Annotated[List[Dict[str, str]], operator.add]
    phase: Literal[
        "initial_inquiry",
        "awaiting_response",
        "providing_details",
        "clarifying",
        "reviewing_proposal", 
        "negotiating",
        "confirming",
        "completed"
    ]
    provided_info: Dict[str, bool]
    persona_name: str
    persona_type: Optional[str]
    persona_traits: List[str]
    forgotten_details: List[str]
    conversation_memory: List[str]
    questions_asked: List[str]
    concerns_raised: List[str]
    metadata: ConversationMetadata
    mood: Literal["excited", "cautious", "frustrated", "satisfied"]
    response_speed: Optional[str]

class WanderoState(TypedDict):
    """State for Wandero bot"""
    collected_info: Dict[str, Any]
    missing_info: List[str]
    conversation_phase: Literal[
        "greeting",
        "gathering_info",
        "clarifying_details",
        "preparing_proposal",
        "proposal_sent",
        "negotiating",
        "booking_confirmed"
    ]
    client_name: Optional[str]
    proposal_version: int
    special_requirements: List[str]
    interaction_count: int

@dataclass
class ConversationResult:
    """Results from a single conversation"""
    persona_name: str
    persona_type: str
    thread_id: str
    start_time: datetime
    end_time: datetime
    total_messages: int
    final_phase: str
    booking_confirmed: bool
    total_duration_seconds: float
    messages: List[Dict[str, str]]
    errors: List[str]

# Persona Library
class PersonaLibrary:
    """Library of diverse client personas for testing"""
    
    @staticmethod
    def get_all_personas() -> Dict[str, Dict[str, Any]]:
        """Return all available personas"""
        return {
            "worried_parent": {
                "name": "Sarah Johnson",
                "email": "sarah.johnson@email.com",
                "type": "Family Vacation Planner",
                "traits": ["detail-oriented", "safety-conscious", "forgetful", "thorough"],
                "family_size": 4,
                "children_ages": [12, 8],
                "concerns": ["child safety", "food allergies", "medical facilities", "kid-friendly activities"],
                "budget": "$4000-6000",
                "destination": "Chile",
                "travel_dates": "July 15-22, 2024",
                "quirks": {
                    "forgets_details": True,
                    "asks_many_questions": True,
                    "response_delay": "medium",
                    "decision_speed": "slow"
                },
                "special_needs": ["Son Jack has severe nut allergy", "Daughter Emma is vegetarian"],
                "communication_style": "polite but anxious, uses lots of questions",
                "typical_messages": [
                    "Is it safe for children?",
                    "What about medical facilities?",
                    "Oh, I forgot to mention..."
                ]
            },
            
            "adventure_couple": {
                "name": "Mike and Lisa Chen",
                "email": "mlchen.adventures@gmail.com",
                "type": "Adventure Seekers",
                "traits": ["spontaneous", "active", "flexible", "enthusiastic"],
                "family_size": 2,
                "children_ages": [],
                "concerns": ["unique experiences", "off-beaten-path", "photography spots"],
                "budget": "$3000-4000",
                "destination": "Chile",
                "travel_dates": "September 5-15, 2024",
                "quirks": {
                    "forgets_details": False,
                    "asks_many_questions": False,
                    "response_delay": "fast",
                    "decision_speed": "fast"
                },
                "special_needs": ["Want extreme sports", "Prefer boutique hotels"],
                "communication_style": "casual, enthusiastic, uses emojis 🎉",
                "typical_messages": [
                    "We want something EPIC!",
                    "The more adventure the better 💪",
                    "Can we add bungee jumping?"
                ]
            },
            
            "budget_backpacker": {
                "name": "Emma Thompson",
                "email": "emma.backpacks@proton.me",
                "type": "Solo Budget Traveler",
                "traits": ["frugal", "independent", "experienced", "negotiator"],
                "family_size": 1,
                "children_ages": [],
                "concerns": ["costs", "hostels", "public transport", "meeting other travelers"],
                "budget": "$1000-1500",
                "destination": "Chile",
                "travel_dates": "May 1-14, 2024",
                "quirks": {
                    "forgets_details": False,
                    "asks_many_questions": True,
                    "response_delay": "slow",
                    "decision_speed": "very_slow"
                },
                "special_needs": ["Vegan diet", "Female-only dorms preferred"],
                "communication_style": "direct, always asking about cheaper options",
                "typical_messages": [
                    "Is there a cheaper option?",
                    "What about hostels instead?",
                    "Can I use public transport?"
                ]
            },
            
            "corporate_planner": {
                "name": "David Martinez",
                "email": "d.martinez@techcorp.com",
                "type": "Corporate Event Planner",
                "traits": ["professional", "demanding", "organized", "impatient"],
                "family_size": 15,
                "children_ages": [],
                "concerns": ["meeting facilities", "wifi quality", "airport transfers", "team building"],
                "budget": "$25000-30000",
                "destination": "Chile",
                "travel_dates": "August 10-13, 2024",
                "quirks": {
                    "forgets_details": False,
                    "asks_many_questions": True,
                    "response_delay": "very_fast",
                    "decision_speed": "medium"
                },
                "special_needs": ["Need conference room for 15", "Some vegetarians in group", "CEO has mobility issues"],
                "communication_style": "formal, bullet points, expects quick responses",
                "typical_messages": [
                    "Please confirm ASAP",
                    "Need detailed breakdown",
                    "What are the cancellation terms?"
                ]
            },
            
            "retired_couple": {
                "name": "Robert and Patricia Williams",
                "email": "williams.travels@aol.com",
                "type": "Luxury Seniors",
                "traits": ["leisurely", "comfort-focused", "chatty", "particular"],
                "family_size": 2,
                "children_ages": [],
                "concerns": ["comfort", "accessibility", "medical care", "pace of tour"],
                "budget": "$8000-12000",
                "destination": "Chile",
                "travel_dates": "October 1-14, 2024",
                "quirks": {
                    "forgets_details": True,
                    "asks_many_questions": True,
                    "response_delay": "very_slow",
                    "decision_speed": "slow"
                },
                "special_needs": ["Robert uses a cane", "Patricia is diabetic", "Need ground floor rooms"],
                "communication_style": "very polite, lengthy emails, share personal stories",
                "typical_messages": [
                    "We're not as young as we used to be...",
                    "My husband Robert has bad knees",
                    "We visited Peru in 1987 and loved it!"
                ]
            }
        }
    
    @staticmethod
    def get_persona(persona_type: str) -> Dict[str, Any]:
        """Get a specific persona by type"""
        personas = PersonaLibrary.get_all_personas()
        return personas.get(persona_type, personas["worried_parent"])

# Original persona creation (kept for compatibility)
def create_persona():
    """Create a worried parent planning a family vacation"""
    return {
        "name": "Sarah Johnson",
        "traits": ["detail-oriented", "safety-conscious", "forgetful"],
        "family_size": 4,
        "children_ages": [12, 8],
        "concerns": ["child safety", "food allergies", "medical facilities"],
        "budget": "$4000-6000",
        "destination": "Chile",
        "travel_dates": "July 15-22, 2024",
        "quirk": "Forgets to mention important details initially"
    }

# Utility functions
def safe_llm_invoke(prompt: str, delay_seconds: int = 5, node_name: str = "unknown") -> str:
    """Safely invoke LLM with comprehensive error handling and tracking"""
    print(f"🤖 [{node_name}] Making LLM request...")
    print(f"⏰ [{node_name}] Waiting {delay_seconds} seconds before API call...")
    sleep(delay_seconds)
    
    try:
        print(f"📡 [{node_name}] Sending request to Gemini API...")
        response = llm.invoke(prompt).content
        print(f"✅ [{node_name}] API request successful!")
        print(f"📝 [{node_name}] Response preview: {response[:100]}...")
        
        print(f"⏰ [{node_name}] Post-request delay (2 seconds)...")
        sleep(2)
        
        return response
        
    except Exception as e:
        print(f"❌ [{node_name}] API Error: {e}")
        
        if "429" in str(e) or "quota" in str(e).lower() or "rate" in str(e).lower():
            print(f"🚨 [{node_name}] RATE LIMIT HIT! Implementing backoff strategy...")
            print(f"⏰ [{node_name}] Waiting 45 seconds for rate limit cooldown...")
            sleep(45)
            
            print(f"🔄 [{node_name}] Retrying API call...")
            try:
                response = llm.invoke(prompt).content
                print(f"✅ [{node_name}] Retry successful!")
                return response
            except Exception as retry_error:
                print(f"❌ [{node_name}] Retry failed: {retry_error}")
                print(f"🎭 [{node_name}] Using fallback response...")
                return f"I'm interested in planning our family trip to Chile. Please let me know what information you need from {create_persona()['name']}."
        
        print(f"🎭 [{node_name}] Using fallback response due to unexpected error...")
        return "Thank you for your response. I'm interested in planning our trip."

def print_state_debug(state: ClientState, node_name: str):
    """Print detailed state information for debugging"""
    print(f"\n🔍 [{node_name}] STATE DEBUG:")
    print(f"   📍 Phase: {state.get('phase', 'unknown')}")
    print(f"   👤 Persona: {state.get('persona_name', 'unknown')}")
    print(f"   😊 Mood: {state.get('mood', 'unknown')}")
    print(f"   📊 Messages count: {len(state.get('messages', []))}")
    print(f"   ✅ Provided info: {state.get('provided_info', {})}")
    print(f"   🤔 Forgotten details: {state.get('forgotten_details', [])}")
    print(f"   🧠 Memory points: {len(state.get('conversation_memory', []))}")
    
    messages = state.get('messages', [])
    if messages:
        print(f"   💬 Recent messages:")
        for msg in messages[-2:]:
            role_emoji = "👤" if msg['role'] == 'client' else "🏢" if msg['role'] == 'wandero' else "⚙️"
            content_preview = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
            print(f"      {role_emoji} {msg['role']}: {content_preview}")

# Original nodes (kept for compatibility)
def initial_inquiry_node(state: ClientState) -> Dict:
    """Generate the first email to Wandero"""
    print(f"\n{'='*50}")
    print(f"🚀 INITIAL INQUIRY NODE STARTED")
    print(f"{'='*50}")
    
    print_state_debug(state, "INITIAL_INQUIRY")
    
    prompt = f"""You are {state['persona_name']}, a parent planning a family trip.
Write a natural email asking about tours to {create_persona()['destination']}.
BE REALISTIC: Don't include all details. Forget to mention:
- Exact number of people
- Children's ages
- Specific dates

Keep it conversational, 2-3 paragraphs."""
    
    response = safe_llm_invoke(prompt, delay_seconds=6, node_name="INITIAL_INQUIRY")
    
    current_time = datetime.now()
    
    result = {
        "messages": [{"role": "client", "content": response}],
        "phase": "awaiting_response",
        "provided_info": {"destination": True, "dates": False, "family_size": False},
        "questions_asked": ["tours to Chile"],
        "metadata": {
            "thread_id": f"trip_{current_time.strftime('%Y%m%d_%H%M%S')}",
            "started_at": current_time.isoformat(),
            "last_updated": current_time.isoformat(),
            "email_count": 1,
            "current_topic": "Chile family vacation"
        }
    }
    
    print(f"📤 Initial inquiry generated successfully")
    print(f"🔄 Phase updated to: awaiting_response")
    print(f"{'='*50}")
    
    return result

def provide_details_node(state: ClientState) -> Dict:
    """Provide requested information (but forget something!)"""
    print(f"\n{'='*50}")
    print(f"📋 PROVIDE DETAILS NODE STARTED") 
    print(f"{'='*50}")
    
    print_state_debug(state, "PROVIDE_DETAILS")
    
    last_wandero_msg = ""
    for msg in reversed(state["messages"]):
        if msg["role"] == "wandero":
            last_wandero_msg = msg["content"]
            break
    
    if not last_wandero_msg:
        last_wandero_msg = "Please provide more details about your trip"

    prompt = f"""You are {state['persona_name']}. 
Wandero asked: "{last_wandero_msg}"

Provide the information they asked for:
- Family of 4 (2 adults, 2 children)
- Dates: July 15-22, 2024
- Budget: $4000-6000

BUT FORGET to mention your children's ages. This is important - humans forget things!"""

    response = safe_llm_invoke(prompt, delay_seconds=7, node_name="PROVIDE_DETAILS")
    
    # Update conversation memory
    memory_points = state.get("conversation_memory", [])
    memory_points.append("Provided family size and dates")
    memory_points.append("Mentioned budget range")
    
    result = {
        "messages": [{"role": "client", "content": response}],
        "phase": "clarifying",
        "provided_info": {
            **state["provided_info"],
            "dates": True,
            "family_size": True,
            "ages": False
        },
        "forgotten_details": ["children_ages"],
        "conversation_memory": memory_points,
        "metadata": {
            **state.get("metadata", {}),
            "last_updated": datetime.now().isoformat(),
            "email_count": state.get("metadata", {}).get("email_count", 0) + 1
        }
    }
    
    print(f"📤 Details provided successfully")
    print(f"🤔 Added to forgotten details: children_ages")
    print(f"{'='*50}")
    
    return result

def send_correction_node(state: ClientState) -> Dict:
    """Send a follow-up email with forgotten information"""
    print(f"\n{'='*50}")
    print(f"🔧 SEND CORRECTION NODE STARTED")
    print(f"{'='*50}")
    
    print_state_debug(state, "SEND_CORRECTION")
    
    forgotten_details = state.get("forgotten_details", [])
    
    if "children_ages" in forgotten_details:
        prompt = f"""You are {state['persona_name']}.
Write a SHORT follow-up email saying:
"Oh, I forgot to mention - my children are 12 and 8 years old"

Make it natural and apologetic."""

        response = safe_llm_invoke(prompt, delay_seconds=5, node_name="SEND_CORRECTION")
        
        # Update memory
        memory_points = state.get("conversation_memory", [])
        memory_points.append("Remembered to mention children's ages")
        
        result = {
            "messages": [
                {"role": "system", "content": "[Sent 5 minutes later]"},
                {"role": "client", "content": response}
            ],
            "provided_info": {**state["provided_info"], "ages": True},
            "forgotten_details": [],
            "conversation_memory": memory_points,
            "metadata": {
                **state.get("metadata", {}),
                "last_updated": datetime.now().isoformat(),
                "email_count": state.get("metadata", {}).get("email_count", 0) + 1
            }
        }
        
        print(f"📤 Correction email sent successfully")
        print(f"✅ Updated provided_info with ages: True")
        print(f"🧹 Cleared forgotten_details")
        print(f"{'='*50}")
        
        return result
    
    print(f"ℹ️ No corrections needed")
    print(f"{'='*50}")
    return {}

# New persona-aware nodes
def persona_aware_inquiry_node(state: ClientState) -> Dict:
    """Generate initial inquiry based on specific persona characteristics"""
    print(f"\n{'='*50}")
    print(f"🎭 PERSONA-AWARE INQUIRY NODE")
    print(f"👤 Persona: {state['persona_name']}")
    print(f"{'='*50}")
    
    # Get full persona details
    persona_type = state.get("persona_type", "worried_parent")
    persona = PersonaLibrary.get_persona(persona_type)
    
    # Build persona-specific prompt
    prompt = f"""You are {persona['name']}, a {persona['type']}.
Your personality traits: {', '.join(persona['traits'])}
Your communication style: {persona['communication_style']}
Your main concerns: {', '.join(persona['concerns'][:2])}

Write your first email to a travel agency about a trip to {persona['destination']}.

IMPORTANT: Match the persona's style:
- {'Use emojis' if 'emoji' in persona['communication_style'] else 'Be formal'}
- {'Ask many questions' if persona['quirks']['asks_many_questions'] else 'Keep it brief'}
- {'Mention your experience' if persona['type'] == 'Solo Budget Traveler' else ''}
- {'Be anxious about safety' if 'safety-conscious' in persona['traits'] else ''}

Based on the quirks, {'FORGET to mention key details like exact dates or group size' if persona['quirks']['forgets_details'] else 'Include all basic information'}.

Make it sound like {persona['name']} would really write it."""

    response = safe_llm_invoke(prompt, delay_seconds=5, node_name=f"INQUIRY_{persona['name']}")
    
    # Add persona-specific metadata
    result = {
        "messages": [{"role": "client", "content": response}],
        "phase": "awaiting_response",
        "provided_info": {"destination": True, "inquiry_sent": True},
        "questions_asked": [],
        "persona_type": persona_type,
        "response_speed": persona['quirks']['response_delay'],
        "metadata": {
            **state.get("metadata", {}),
            "persona_type": persona_type,
            "expected_budget": persona['budget'],
            "group_size": persona['family_size']
        }
    }
    
    print(f"✅ Generated {persona['name']}'s initial inquiry")
    return result

def persona_aware_response_node(state: ClientState) -> Dict:
    """Generate responses that match persona personality"""
    persona_type = state.get("persona_type", "worried_parent")
    persona = PersonaLibrary.get_persona(persona_type)
    
    # Get last Wandero message
    last_wandero_msg = ""
    for msg in reversed(state["messages"]):
        if msg["role"] == "wandero":
            last_wandero_msg = msg["content"]
            break
    
    # Analyze what Wandero is asking/saying
    msg_lower = last_wandero_msg.lower()
    is_proposal = "$" in last_wandero_msg and "itinerary" in msg_lower
    is_question = "?" in last_wandero_msg
    is_confirmation = "confirm" in msg_lower or "booking" in msg_lower
    
    # Build persona-specific response
    mood = state.get("mood", "neutral")
    
    if persona_type == "worried_parent":
        if is_proposal:
            prompt = f"""You are {persona['name']}, reviewing a travel proposal.
Your main concern: Is this safe for my children?
Ask about: medical facilities, food allergy accommodations, child supervision
Mention: {random.choice(persona['special_needs'])}
Style: Anxious but polite"""
        else:
            prompt = f"""You are {persona['name']}, providing requested information.
Include: {persona['family_size']} people, dates {persona['travel_dates']}, budget {persona['budget']}
BUT FORGET: One important detail about {random.choice(['ages', 'allergy', 'dates'])}
Add a worried question about safety"""
            
    elif persona_type == "adventure_couple":
        if is_proposal:
            prompt = f"""You are {persona['name']}, reviewing an adventure proposal.
React with: EXCITEMENT! Use emojis! 🎉🏔️
Ask about: Adding more extreme activities, photography tours
Style: Enthusiastic and spontaneous"""
        else:
            prompt = f"""You are {persona['name']}, eager adventure seekers.
Mention: Just the 2 of us, {persona['travel_dates']}, budget {persona['budget']}
Emphasize: We want MAXIMUM adventure
Use casual language and emojis"""
            
    elif persona_type == "budget_backpacker":
        if is_proposal:
            prompt = f"""You are {persona['name']}, reviewing a proposal.
First reaction: "This seems expensive..."
Ask about: Cheaper accommodations, public transport options, hostel availability
Negotiate: Try to get a better price
Style: Direct but friendly"""
        else:
            prompt = f"""You are {persona['name']}, solo budget traveler.
Mention: Just myself, {persona['travel_dates']}, tight budget {persona['budget']}
Ask immediately about: Hostel options, cheapest transport
Mention: {persona['special_needs'][0]}"""
            
    elif persona_type == "corporate_planner":
        if is_proposal:
            prompt = f"""You are {persona['name']}, reviewing a corporate proposal.
Style: Professional, use bullet points
Ask about:
• Meeting room specifications
• WiFi bandwidth
• Catering options
• Team building activities
• Cancellation policy
Be somewhat demanding"""
        else:
            prompt = f"""You are {persona['name']}, corporate planner.
State clearly:
- 15 executives
- Dates: {persona['travel_dates']}
- Budget: {persona['budget']}
- Need: Conference facilities
End with: "Please respond by EOD" """
            
    elif persona_type == "retired_couple":
        if is_proposal:
            prompt = f"""You are {persona['name']}, reviewing a proposal.
Share a story: "This reminds me of our trip to..."
Express concern about: Walking distances, elevation, pace
Ask about: Accessibility, medical facilities nearby
Style: Chatty, warm, but particular about comfort"""
        else:
            prompt = f"""You are {persona['name']}, retired travelers.
Chat warmly about: Looking forward to this trip
Mention casually: {persona['special_needs'][0]}
Share: "We're celebrating our 45th anniversary"
Ask about: Comfortable accommodations, not too much walking"""
    else:
        prompt = f"You are {persona['name']}. Respond naturally to: {last_wandero_msg}"
    
    # Add universal context
    prompt += f"\n\nCurrent mood: {mood}"
    prompt += f"\nPrevious messages: {len(state['messages'])}"
    prompt += "\n\nWrite a natural email response that fits your personality."
    
    response = safe_llm_invoke(prompt, delay_seconds=4, node_name=f"RESPONSE_{persona['name']}")
    
    return {
        "messages": [{"role": "client", "content": response}],
        "metadata": {
            **state.get("metadata", {}),
            "last_updated": datetime.now().isoformat(),
            "email_count": state.get("metadata", {}).get("email_count", 0) + 1
        }
    }

# Enhanced nodes for stateful Wandero interaction
def review_proposal_node(state: ClientState) -> Dict:
    """Review Wandero's proposal and respond"""
    print(f"\n{'='*50}")
    print(f"📄 REVIEW PROPOSAL NODE STARTED")
    print(f"{'='*50}")
    
    # Find the latest Wandero proposal
    last_wandero_msg = ""
    for msg in reversed(state["messages"]):
        if msg["role"] == "wandero":
            last_wandero_msg = msg["content"]
            break
    
    # Analyze if it's a proposal
    has_pricing = "$" in last_wandero_msg
    has_itinerary = "day" in last_wandero_msg.lower()
    
    if has_pricing and has_itinerary:
        # Generate client response to proposal
        persona_traits = state.get("persona_traits", [])
        concerns = []
        
        if "safety-conscious" in persona_traits:
            concerns.append("safety measures")
        if "detail-oriented" in persona_traits:
            concerns.append("specific activity details")
        
        prompt = f"""You are {state['persona_name']} reviewing a travel proposal.
        
The proposal includes: pricing around $5,200 and an 8-day itinerary.

Based on your personality traits ({', '.join(persona_traits)}), write a response that:
1. Shows interest in the proposal
2. Asks about {' and '.join(concerns) if concerns else 'any additional services'}
3. Mentions your child has a nut allergy (important detail!)
4. Asks about payment terms

Keep it natural and conversational."""
        
        response = safe_llm_invoke(prompt, delay_seconds=6, node_name="REVIEW_PROPOSAL")
        
        # Update state
        memory_points = state.get("conversation_memory", [])
        memory_points.append("Received detailed proposal")
        memory_points.append("Mentioned child's nut allergy")
        
        concerns_raised = state.get("concerns_raised", [])
        concerns_raised.append("nut allergy")
        
        result = {
            "messages": [{"role": "client", "content": response}],
            "phase": "negotiating",
            "conversation_memory": memory_points,
            "concerns_raised": concerns_raised,
            "mood": "cautious",
            "metadata": {
                **state.get("metadata", {}),
                "last_updated": datetime.now().isoformat(),
                "email_count": state.get("metadata", {}).get("email_count", 0) + 1
            }
        }
        
        print(f"📤 Proposal review sent")
        print(f"🔄 Phase updated to: negotiating")
        print(f"⚠️ Raised concern: nut allergy")
        print(f"{'='*50}")
        
        return result
    
    # If no proposal found, continue conversation
    print(f"ℹ️ No proposal found, continuing conversation")
    return {}

def confirm_booking_node(state: ClientState) -> Dict:
    """Confirm the booking after negotiations"""
    print(f"\n{'='*50}")
    print(f"✅ CONFIRM BOOKING NODE STARTED")
    print(f"{'='*50}")
    
    prompt = f"""You are {state['persona_name']} ready to confirm your Chile trip booking.

Write a brief email that:
1. Confirms you want to proceed with the booking
2. Asks about next steps for payment
3. Thanks the agent warmly

Keep it short and enthusiastic!"""
    
    response = safe_llm_invoke(prompt, delay_seconds=5, node_name="CONFIRM_BOOKING")
    
    result = {
        "messages": [{"role": "client", "content": response}],
        "phase": "completed",
        "mood": "satisfied",
        "metadata": {
            **state.get("metadata", {}),
            "last_updated": datetime.now().isoformat(),
            "email_count": state.get("metadata", {}).get("email_count", 0) + 1
        }
    }
    
    print(f"📤 Booking confirmation sent")
    print(f"🔄 Phase updated to: completed")
    print(f"😊 Mood: satisfied")
    print(f"{'='*50}")
    
    return result

def analyze_conversation_node(state: ClientState) -> Dict:
    """Analyze the conversation history to understand context"""
    print(f"\n{'='*50}")
    print(f"🧠 ANALYZE CONVERSATION NODE STARTED")
    print(f"{'='*50}")
    
    wandero_messages = [
        msg["content"] for msg in state.get("messages", [])
        if msg["role"] == "wandero"
    ]
    
    memory_points = state.get("conversation_memory", [])
    
    if wandero_messages:
        last_msg = wandero_messages[-1].lower()
        
        if "thank you for" in last_msg:
            memory_points.append("Wandero acknowledged our message")
        if "?" in last_msg:
            memory_points.append("Wandero asked us questions")
        if "$" in last_msg or "price" in last_msg:
            memory_points.append("Price was mentioned")
    
    # Determine mood based on conversation
    mood = state.get("mood", "excited")
    if len(wandero_messages) > 3 and any("still need" in msg.lower() for msg in wandero_messages[-2:]):
        mood = "frustrated"
    elif any("perfect" in msg.lower() or "confirmed" in msg.lower() for msg in wandero_messages):
        mood = "satisfied"
    elif len(wandero_messages) > 1:
        mood = "cautious"
    
    print(f"📊 Analysis complete - Mood: {mood}, Memory points: {len(memory_points)}")
    print(f"{'='*50}")
    
    return {
        "conversation_memory": memory_points,
        "mood": mood
    }

# Stateful Wandero implementation
class StatefulWandero:
    """Enhanced Wandero bot with state tracking and realistic responses"""
    
    def __init__(self):
        self.state = self._initialize_state()
        self.company_info = {
            "name": "Chile Adventures Ltd.",
            "agent": "Maria Rodriguez",
            "email": "maria@chileadventures.com",
            "response_time": "2-4 hours"
        }
        
    def _initialize_state(self) -> WanderoState:
        """Initialize Wandero's state"""
        return {
            "collected_info": {},
            "missing_info": [
                "travel_dates",
                "group_size",
                "children_ages", 
                "budget",
                "special_requirements"
            ],
            "conversation_phase": "greeting",
            "client_name": None,
            "proposal_version": 0,
            "special_requirements": [],
            "interaction_count": 0
        }
    
    def process_email(self, client_message: str, client_state: Optional[ClientState] = None) -> str:
        """Process client email with state awareness"""
        
        self.state["interaction_count"] += 1
        
        # Extract client name if available
        if client_state and not self.state["client_name"]:
            self.state["client_name"] = client_state.get("persona_name", "Valued Customer")
        
        # Analyze the message
        self._extract_information(client_message)
        
        # Determine response based on phase
        response_method = {
            "greeting": self._greeting_response,
            "gathering_info": self._gathering_info_response,
            "clarifying_details": self._clarifying_response,
            "preparing_proposal": self._proposal_response,
            "proposal_sent": self._handle_proposal_feedback,
            "negotiating": self._negotiation_response,
            "booking_confirmed": self._booking_confirmation
        }
        
        method = response_method.get(self.state["conversation_phase"], self._default_response)
        return method(client_message)
    
    def _extract_information(self, message: str) -> None:
        """Extract information from client message"""
        msg_lower = message.lower()
        
        # Extract travel dates
        if "july" in msg_lower:
            date_pattern = r'july\s+(\d+)[-\s]+(?:to\s+)?(\d+)'
            date_match = re.search(date_pattern, msg_lower)
            if date_match:
                self.state["collected_info"]["travel_dates"] = f"July {date_match.group(1)}-{date_match.group(2)}, 2024"
                self.state["missing_info"] = [x for x in self.state["missing_info"] if x != "travel_dates"]
        
        # Extract group size
        if any(num in msg_lower for num in ["2 adults", "two adults", "4 people", "four people", "family of 4"]):
            self.state["collected_info"]["adults"] = 2
            self.state["collected_info"]["group_size"] = 4
            self.state["missing_info"] = [x for x in self.state["missing_info"] if x != "group_size"]
        elif "15" in msg_lower and ("executive" in msg_lower or "people" in msg_lower):
            self.state["collected_info"]["group_size"] = 15
            self.state["missing_info"] = [x for x in self.state["missing_info"] if x != "group_size"]
        
        # Extract children ages
        age_pattern = r'(?:ages?|aged?)\s*(\d+)\s*(?:and|&)\s*(\d+)'
        age_match = re.search(age_pattern, msg_lower)
        if age_match:
            ages = [int(age_match.group(1)), int(age_match.group(2))]
            self.state["collected_info"]["children_ages"] = ages
            self.state["collected_info"]["children_count"] = len(ages)
            self.state["missing_info"] = [x for x in self.state["missing_info"] if x != "children_ages"]
        elif "12" in msg_lower and "8" in msg_lower:
            self.state["collected_info"]["children_ages"] = [12, 8]
            self.state["collected_info"]["children_count"] = 2
            self.state["missing_info"] = [x for x in self.state["missing_info"] if x != "children_ages"]
        
        # Extract budget
        budget_pattern = r'\$?([\d,]+)\s*[-to]+\s*\$?([\d,]+)'
        budget_match = re.search(budget_pattern, message)
        if budget_match:
            min_budget = int(budget_match.group(1).replace(',', ''))
            max_budget = int(budget_match.group(2).replace(',', ''))
            self.state["collected_info"]["budget_range"] = (min_budget, max_budget)
            self.state["missing_info"] = [x for x in self.state["missing_info"] if x != "budget"]
        
        # Extract special requirements
        if "allerg" in msg_lower:
            if "nut" in msg_lower:
                self.state["special_requirements"].append("nut allergy")
            self.state["collected_info"]["has_allergies"] = True
            if "special_requirements" in self.state["missing_info"]:
                self.state["missing_info"].remove("special_requirements")
        
        # Update conversation phase based on collected info
        self._update_phase()

    def _greeting_response(self, message: str) -> str:
        """Initial greeting response"""
        self.state["conversation_phase"] = "gathering_info"
        
        return f"""Dear {self.state.get('client_name', 'Valued Customer')},

Thank you for your interest in exploring Chile with {self.company_info['name']}! I'm {self.company_info['agent']}, and I'll be your dedicated travel consultant for this exciting journey.

Chile offers an incredible diversity of experiences - from the otherworldly Atacama Desert to the stunning landscapes of Patagonia, vibrant cities, and pristine coastlines. For families, we specialize in creating balanced itineraries that combine adventure, culture, and relaxation.

To design the perfect Chilean adventure for your family, could you please share:
• Your preferred travel dates
• Number of travelers (adults and children with ages)
• Approximate budget for the trip
• Any special interests or must-see destinations
• Accommodation preferences (hotels, lodges, or mix)
• Any dietary restrictions or special requirements

I'm here to help create memories that will last a lifetime!

Warm regards,
{self.company_info['agent']}
Senior Travel Consultant
{self.company_info['name']}
📧 {self.company_info['email']}
⏰ Response time: {self.company_info['response_time']}"""

    def _gathering_info_response(self, message: str) -> str:
        """Response while gathering information"""
        
        # Acknowledge what we received
        ack_parts = []
        if "travel_dates" in self.state["collected_info"]:
            ack_parts.append(f"✓ Travel dates: {self.state['collected_info']['travel_dates']}")
        if "group_size" in self.state["collected_info"]:
            ack_parts.append(f"✓ Group size: {self.state['collected_info']['group_size']} travelers")
        if "budget_range" in self.state["collected_info"]:
            budget = self.state["collected_info"]["budget_range"]
            ack_parts.append(f"✓ Budget: ${budget[0]:,} - ${budget[1]:,}")
        
        acknowledgment = "\n".join(ack_parts) if ack_parts else ""
        
        # Determine what's still missing
        missing_prompts = {
            "children_ages": "• The ages of your children (this helps us plan age-appropriate activities)",
            "budget": "• Your approximate budget for the trip",
            "travel_dates": "• Your preferred travel dates",
            "special_requirements": "• Any special requirements, dietary restrictions, or must-see places"
        }
        
        missing_items = [missing_prompts[item] for item in self.state["missing_info"] if item in missing_prompts]
        
        if len(missing_items) <= 2:  # Almost have everything
            self.state["conversation_phase"] = "clarifying_details"
            
        return f"""Dear {self.state.get('client_name', 'Valued Customer')},

Thank you for the information! I'm excited to help plan your Chilean adventure.

{f"I've noted the following details:{chr(10)}{acknowledgment}" if acknowledgment else ""}

{"To create the perfect itinerary for your family, I just need a few more details:" if missing_items else "Great! I have all the basic information I need."}
{chr(10).join(missing_items) if missing_items else ""}

{self._add_helpful_tips()}

Looking forward to your response!

Best regards,
{self.company_info['agent']}"""

    def _add_helpful_tips(self) -> str:
        """Add helpful tips based on what we know"""
        tips = []
        
        if "travel_dates" in self.state["collected_info"] and "july" in self.state["collected_info"]["travel_dates"].lower():
            tips.append("💡 July is winter in Chile - perfect for skiing in the Andes or visiting the Atacama Desert!")
        
        if "children_ages" in self.state["collected_info"]:
            ages = self.state["collected_info"]["children_ages"]
            if any(age < 10 for age in ages):
                tips.append("🎈 We have fantastic family-friendly accommodations with kids' clubs and activities")
        
        return "\n".join(tips)
    
    def _proposal_response(self, message: str) -> str:
        """Generate a detailed proposal"""
        self.state["conversation_phase"] = "proposal_sent"
        self.state["proposal_version"] += 1
        
        # Calculate pricing
        budget = self.state["collected_info"].get("budget_range", (4000, 6000))
        adults = self.state["collected_info"].get("adults", 2)
        children = self.state["collected_info"].get("children_count", 2)
        ages = self.state["collected_info"].get("children_ages", [12, 8])
        
        # Price calculation
        base_adult_price = 1400
        child_discount = 0.3
        adult_total = adults * base_adult_price
        child_total = sum(base_adult_price * (1 - child_discount) for age in ages)
        subtotal = adult_total + child_total
        
        # Add some services
        services = {
            "Airport transfers": 200,
            "Travel insurance": 180,
            "Guided tours": 600,
            "Special dietary arrangements": 100 if self.state["special_requirements"] else 0
        }
        
        total = subtotal + sum(services.values())
        
        return f"""Dear {self.state.get('client_name', 'Family')},

I'm delighted to present your personalized "Chilean Family Discovery" itinerary!

📅 **TRAVEL DATES**: {self.state["collected_info"].get("travel_dates", "July 15-22, 2024")}
👨‍👩‍👧‍👦 **TRAVELERS**: {adults} Adults + {children} Children (ages {', '.join(map(str, ages))})

🗺️ **YOUR 8-DAY ITINERARY**

**Day 1 - Welcome to Santiago**
• Private airport transfer to Hotel Plaza San Francisco (Family Suite)
• Welcome dinner at hotel with Chilean specialties
• Rest and acclimate

**Day 2 - Santiago Discovery**
• Morning: Interactive tour of Pre-Columbian Art Museum
• Afternoon: Cable car ride up San Cristóbal Hill
• Evening: Traditional dinner in Bellavista neighborhood

**Day 3-4 - Atacama Desert Adventure**
• Fly to Calama, transfer to San Pedro de Atacama
• Stay at Hotel Cumbres (Family Rooms with mountain views)
• Day 3: Valley of the Moon sunset tour
• Day 4: Flamingo watching at Chaxa Lagoon + Atacama Salt Flats

**Day 5 - Atacama Experiences**
• Morning: Tatio Geysers (early start with breakfast)
• Afternoon: Swimming at Puritama Hot Springs
• Evening: Stargazing tour (world's clearest skies!)

**Day 6 - Return to Santiago**
• Morning flight back to Santiago
• Afternoon: Visit La Chascona (Pablo Neruda's house)
• Cooking class: Learn to make empanadas!

**Day 7 - Coastal Excursion**
• Day trip to Valparaíso and Viña del Mar
• Explore colorful hillside neighborhoods
• Beach time and seafood lunch
• Return to Santiago

**Day 8 - Departure**
• Morning at leisure
• Private transfer to airport

💰 **INVESTMENT BREAKDOWN**

Accommodation (7 nights):           ${int(adult_total + child_total):,}
Domestic flights (4 segments):      $1,200
All guided tours & activities:      ${services['Guided tours']:,}
Private transfers:                  ${services['Airport transfers']:,}
Travel insurance:                   ${services['Travel insurance']:,}
{"Special dietary accommodations:    $" + str(services['Special dietary arrangements']) if services['Special dietary arrangements'] else ""}

**TOTAL INVESTMENT: ${int(total):,}**
*All prices in USD. Includes all taxes.*

✨ **WHAT'S INCLUDED**
• All accommodations in family rooms/suites
• Daily breakfast + 4 lunches + 2 dinners
• All entrance fees and activities mentioned
• English-speaking guides throughout
• 24/7 local support
{f"• Special arrangements for {', '.join(self.state['special_requirements'])}" if self.state['special_requirements'] else ""}

🎁 **EXCLUSIVE FAMILY BENEFITS**
• Kids eat free at hotel restaurants
• Chilean recipe book as souvenir
• Traditional craft workshop for children
• Flexible meal times to accommodate young travelers

Would you like to proceed with this itinerary, or would you prefer any modifications?

Warmly,
{self.company_info['agent']}

P.S. I can also arrange optional activities like horseback riding, sandboarding, or cooking classes if interested!"""
        
    def _handle_proposal_feedback(self, message: str) -> str:
        """Handle client response to proposal"""
        msg_lower = message.lower()
        
        # Check for acceptance
        if any(word in msg_lower for word in ["perfect", "great", "book", "proceed", "confirm"]):
            self.state["conversation_phase"] = "booking_confirmed"
            return self._booking_confirmation(message)
        
        # Check for modifications
        if any(word in msg_lower for word in ["change", "modify", "different", "instead", "too expensive", "cheaper"]):
            self.state["conversation_phase"] = "negotiating"
            return self._negotiation_response(message)
        
        # Check for special requirements
        if "allerg" in msg_lower or "diet" in msg_lower:
            return self._handle_special_requirements(message)
        
        # Questions about the proposal
        return self._answer_questions(message)
    
    def _handle_special_requirements(self, message: str) -> str:
        """Handle special dietary or other requirements"""
        return f"""Dear {self.state.get('client_name', 'Valued Customer')},

Thank you for letting me know about the nut allergy! This is extremely important, and I'll ensure all necessary arrangements are made.

🛡️ **ALLERGY SAFETY MEASURES**:
• All hotels will be notified in advance
• Restaurant pre-screening for all included meals
• Emergency medical facility list provided
• Allergy cards in Spanish for your use
• Guide briefed on allergy protocols

I'll update the itinerary to include these safety measures at no additional cost. 
Your family's safety is our top priority!

The total investment remains at ${self.state['collected_info'].get('budget_range', (5000, 5500))[1]:,}.

Does everything else in the itinerary look good to you?

Best regards,
{self.company_info['agent']}"""
    
    def _negotiation_response(self, message: str) -> str:
        """Handle modification requests"""
        msg_lower = message.lower()
        modifications = []
        
        if "expensive" in msg_lower or "cheaper" in msg_lower:
            modifications.append("budget_adjustment")
        if "shorter" in msg_lower or "longer" in msg_lower:
            modifications.append("duration_change")
        if "different" in msg_lower and "hotel" in msg_lower:
            modifications.append("accommodation_change")
        
        return f"""Dear {self.state.get('client_name', 'Valued Customer')},

Of course! I'm happy to adjust the itinerary to better suit your needs.

{self._generate_modifications(modifications)}

Would you like me to revise the full proposal with these changes?

Best regards,
{self.company_info['agent']}"""

    def _booking_confirmation(self, message: str) -> str:
        """Generate booking confirmation"""
        
        return f"""Dear {self.state.get('client_name', 'Family')},

🎉 Wonderful news! I'm thrilled to confirm your Chilean Family Discovery adventure!

**BOOKING CONFIRMATION**
Confirmation #: CHA-2024-{random.randint(1000, 9999)}
Travel Dates: {self.state["collected_info"].get("travel_dates", "July 15-22, 2024")}

**NEXT STEPS:**

1️⃣ **Secure Your Booking** (Due within 48 hours)
   • Deposit required: 30% (${int(self.state["collected_info"].get("budget_range", (4000, 6000))[1] * 0.3):,})
   • Payment methods: Credit card, bank transfer, or PayPal
   • Payment link: [Secure payment portal will be sent separately]

2️⃣ **Documentation Required** (Due by June 15)
   • Passport copies for all travelers
   • Travel insurance details
   • Emergency contact information
   • {f"Medical information for dietary requirements" if self.state["special_requirements"] else "Any special requirements"}

3️⃣ **You'll Receive Soon**
   • Detailed day-by-day itinerary (within 24 hours)
   • Packing list for Chile's varied climates
   • Restaurant recommendations
   • Emergency contact numbers
   • Digital travel guide

4️⃣ **30 Days Before Departure**
   • Final payment due
   • Weather forecast update
   • Last-minute tips
   • WhatsApp group with your guides

**IMPORTANT REMINDERS:**
✓ Passports must be valid for 6 months from travel date
✓ No visa required for US citizens (up to 90 days)
✓ Yellow fever vaccination not required
✓ Chilean pesos recommended (ATMs widely available)

I'll be in touch within 24 hours with your detailed itinerary and payment link.

Thank you for choosing {self.company_info['name']} for your family adventure! 
I can't wait to help create these special memories for you.

¡Nos vemos en Chile! (See you in Chile!)

{self.company_info['agent']}
Senior Travel Consultant

📱 WhatsApp: +56 9 1234 5678
📧 {self.company_info['email']}
🌐 Emergency line: +56 2 2345 6789"""
    
    def _update_phase(self) -> None:
        """Update conversation phase based on collected information"""
        essential_info = ["travel_dates", "group_size", "budget"]
        has_essential = all(info in self.state["collected_info"] for info in essential_info)
        
        if has_essential and self.state["conversation_phase"] == "gathering_info":
            if "children_ages" not in self.state["collected_info"]:
                self.state["conversation_phase"] = "clarifying_details"
            else:
                self.state["conversation_phase"] = "preparing_proposal"
    
    def _clarifying_response(self, message: str) -> str:
        """Response when clarifying final details"""
        missing = self.state["missing_info"]
        
        if not missing or (len(missing) == 1 and missing[0] == "special_requirements"):
            self.state["conversation_phase"] = "preparing_proposal"
            return self._proposal_response(message)
        
        return f"""Dear {self.state.get('client_name', 'Valued Customer')},

Excellent! I'm almost ready to create your perfect Chilean itinerary.

Just one final detail - could you please confirm the ages of your children? 
This helps me ensure all activities are age-appropriate and enjoyable for everyone.

Also, please let me know about any dietary restrictions, allergies, or special 
requirements so I can make the necessary arrangements.

I'm already working on some fantastic options for your family!

Best regards,
{self.company_info['agent']}"""

    def _generate_modifications(self, modifications: List[str]) -> str:
        """Generate modification options based on request"""
        options = []
        
        if "budget_adjustment" in modifications:
            options.append("""
💰 **Budget-Friendly Alternatives:**
• Switch to 3-star family hotels: Save $600
• Replace domestic flights with scenic bus journeys: Save $800
• Self-guided tours with audio guides: Save $400
• Adjusted total: $3,200 (saves $2,000)""")
        
        if "duration_change" in modifications:
            options.append("""
📅 **Duration Options:**
• 5-day express tour: Focus on Santiago & Atacama
• 10-day extended journey: Add Patagonia or Lake District
• Weekend getaway: Santiago & Valparaíso only""")
        
        return "\n".join(options) if options else "I'd be happy to explore alternatives that better suit your preferences."
    
    def _answer_questions(self, message: str) -> str:
        """Answer specific questions about the proposal"""
        msg_lower = message.lower()
        
        responses = []
        
        if "weather" in msg_lower:
            responses.append("🌤️ July is winter in Chile - expect 50-65°F in Santiago, cooler in Atacama at night (bring warm layers!)")
        
        if "safe" in msg_lower or "safety" in msg_lower:
            responses.append("🛡️ Chile is one of South America's safest countries. All our destinations are very family-friendly.")
        
        if "food" in msg_lower:
            responses.append("🍽️ Chilean cuisine is mild and kid-friendly. Plenty of international options available too!")
        
        if not responses:
            responses.append("I'd be happy to answer any specific questions about the itinerary!")
        
        return f"""Dear {self.state.get('client_name', 'Valued Customer')},

Great questions! Here's the information you requested:

{chr(10).join(responses)}

Is there anything else you'd like to know about your Chilean adventure?

Best regards,
{self.company_info['agent']}"""
    
    def _default_response(self, message: str) -> str:
        """Default response when phase is unclear"""
        return f"""Dear {self.state.get('client_name', 'Valued Customer')},

Thank you for your message. I want to ensure I provide you with the best possible service.

Could you please clarify what information you need, or let me know how I can help 
with your Chile travel plans?

Best regards,
{self.company_info['agent']}"""

# Parallel Conversation Engine
class ParallelConversationEngine:
    """Engine to run multiple client conversations in parallel"""
    
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.results: List[ConversationResult] = []
        self.active_conversations = {}
        self.lock = threading.Lock()
        
    def run_single_conversation(self, persona_type: str, wandero: StatefulWandero) -> ConversationResult:
        """Run a single conversation for a specific persona"""
        start_time = datetime.now()
        thread_id = f"{persona_type}_{start_time.strftime('%Y%m%d_%H%M%S')}"
        errors = []
        
        print(f"\n🚀 Starting conversation for {persona_type}")
        print(f"🧵 Thread: {thread_id}")
        
        try:
            # Get persona
            persona = PersonaLibrary.get_persona(persona_type)
            
            # Create enhanced graph with persona-specific nodes
            graph = self._create_persona_graph(persona_type)
            config = {"configurable": {"thread_id": thread_id}}
            
            # Initial state
            initial_state = {
                "messages": [],
                "phase": "initial_inquiry",
                "provided_info": {},
                "persona_name": persona["name"],
                "persona_type": persona_type,
                "persona_traits": persona["traits"],
                "forgotten_details": [],
                "conversation_memory": [],
                "questions_asked": [],
                "concerns_raised": [],
                "mood": "excited",
                "metadata": {
                    "thread_id": thread_id,
                    "started_at": start_time.isoformat(),
                    "last_updated": start_time.isoformat(),
                    "email_count": 0,
                    "current_topic": f"{persona['destination']} trip"
                }
            }
            
            # Track active conversation
            with self.lock:
                self.active_conversations[thread_id] = {
                    "persona": persona_type,
                    "status": "active",
                    "current_phase": "starting"
                }
            
            # Run conversation
            all_messages = []
            current_state = initial_state
            max_rounds = 8
            booking_confirmed = False
            
            for round_num in range(max_rounds):
                try:
                    # Update status
                    with self.lock:
                        self.active_conversations[thread_id]["current_phase"] = current_state.get("phase", "unknown")
                    
                    # Client turn
                    result = graph.invoke(current_state, config)
                    current_state = result
                    
                    # Get client message
                    client_messages = [m for m in result["messages"] if m["role"] == "client"]
                    if not client_messages:
                        break
                    
                    latest_msg = client_messages[-1]["content"]
                    all_messages.append({
                        "role": "client",
                        "content": latest_msg,
                        "timestamp": datetime.now().isoformat(),
                        "round": round_num + 1
                    })
                    
                    # Simulate response delay based on persona
                    delay = self._get_response_delay(persona)
                    sleep(delay)
                    
                    # Wandero responds
                    wandero_response = wandero.process_email(latest_msg, result)
                    all_messages.append({
                        "role": "wandero",
                        "content": wandero_response,
                        "timestamp": datetime.now().isoformat(),
                        "round": round_num + 1
                    })
                    
                    # Add to state
                    current_state["messages"].append({
                        "role": "wandero",
                        "content": wandero_response
                    })
                    
                    # Check if complete
                    if wandero.state["conversation_phase"] == "booking_confirmed":
                        booking_confirmed = True
                        break
                        
                except Exception as e:
                    error_msg = f"Round {round_num + 1} error: {str(e)}"
                    errors.append(error_msg)
                    print(f"❌ {thread_id}: {error_msg}")
                    
            # Clean up
            with self.lock:
                del self.active_conversations[thread_id]
                
        except Exception as e:
            errors.append(f"Fatal error: {str(e)}")
            print(f"💥 {thread_id}: Fatal error - {str(e)}")
            
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        return ConversationResult(
            persona_name=persona["name"],
            persona_type=persona_type,
            thread_id=thread_id,
            start_time=start_time,
            end_time=end_time,
            total_messages=len(all_messages),
            final_phase=current_state.get("phase", "unknown"),
            booking_confirmed=booking_confirmed,
            total_duration_seconds=duration,
            messages=all_messages,
            errors=errors
        )
    
    def _create_persona_graph(self, persona_type: str) -> Any:
        """Create a graph with persona-specific behavior"""
        builder = StateGraph(ClientState)
        
        # Use persona-aware nodes
        builder.add_node("initial_inquiry", persona_aware_inquiry_node)
        builder.add_node("respond", persona_aware_response_node)
        builder.add_node("analyze_conversation", analyze_conversation_node)
        builder.add_node("send_correction", send_correction_node)
        
        # Set flow
        builder.set_entry_point("initial_inquiry")
        builder.add_edge("initial_inquiry", "analyze_conversation")
        builder.add_edge("analyze_conversation", "respond")
        
        def router(state):
            if state.get("forgotten_details"):
                return "correction"
            if state.get("phase") == "completed":
                return "end"
            return "continue"
            
        builder.add_conditional_edges(
            "respond",
            router,
            {
                "correction": "send_correction",
                "continue": "analyze_conversation",
                "end": END
            }
        )
        
        builder.add_edge("send_correction", "analyze_conversation")
        
        return builder.compile(checkpointer=memory)
    
    def _get_response_delay(self, persona: Dict) -> float:
        """Get response delay based on persona quirks"""
        delay_map = {
            "very_fast": 0.5,
            "fast": 1.0,
            "medium": 2.0,
            "slow": 3.0,
            "very_slow": 5.0
        }
        return delay_map.get(persona["quirks"]["response_delay"], 2.0)
    
    async def run_parallel_conversations(self, persona_types: List[str]) -> List[ConversationResult]:
        """Run multiple conversations in parallel"""
        print(f"\n🚀 STARTING PARALLEL CONVERSATIONS")
        print(f"👥 Personas: {', '.join(persona_types)}")
        print(f"🔧 Max workers: {self.max_workers}")
        print(f"{'='*60}")
        
        # Create wandero instances for each conversation
        wanderos = {pt: StatefulWandero() for pt in persona_types}
        
        # Run conversations in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for persona_type in persona_types:
                future = executor.submit(
                    self.run_single_conversation,
                    persona_type,
                    wanderos[persona_type]
                )
                futures.append((persona_type, future))
            
            # Monitor progress
            while any(not f[1].done() for f in futures):
                with self.lock:
                    active_count = len(self.active_conversations)
                    if active_count > 0:
                        print(f"\n📊 Active conversations: {active_count}")
                        for tid, info in self.active_conversations.items():
                            print(f"   - {info['persona']}: {info['current_phase']}")
                
                await asyncio.sleep(2)
            
            # Collect results
            for persona_type, future in futures:
                try:
                    result = future.result()
                    self.results.append(result)
                except Exception as e:
                    print(f"❌ Failed to get result for {persona_type}: {e}")
        
        print(f"\n✅ All conversations completed!")
        return self.results

# Analytics and Export Classes
class ConversationAnalytics:
    """Analytics dashboard for conversation results"""
    
    def __init__(self, results: List[ConversationResult]):
        self.results = results
        self.df = self._create_dataframe()
        
    def _create_dataframe(self) -> pd.DataFrame:
        """Convert results to pandas DataFrame"""
        data = []
        for r in self.results:
            data.append({
                "persona_name": r.persona_name,
                "persona_type": r.persona_type,
                "thread_id": r.thread_id,
                "start_time": r.start_time,
                "end_time": r.end_time,
                "duration_seconds": r.total_duration_seconds,
                "total_messages": r.total_messages,
                "client_messages": sum(1 for m in r.messages if m["role"] == "client"),
                "wandero_messages": sum(1 for m in r.messages if m["role"] == "wandero"),
                "final_phase": r.final_phase,
                "booking_confirmed": r.booking_confirmed,
                "errors": len(r.errors),
                "success": len(r.errors) == 0 and r.booking_confirmed
            })
        return pd.DataFrame(data)
    
    def generate_summary_report(self) -> str:
        """Generate a text summary report"""
        report = []
        report.append("="*80)
        report.append("📊 CONVERSATION ANALYTICS SUMMARY REPORT")
        report.append("="*80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Overall statistics
        report.append("📈 OVERALL STATISTICS")
        report.append("-"*40)
        report.append(f"Total conversations: {len(self.results)}")
        report.append(f"Successful bookings: {self.df['booking_confirmed'].sum()} ({self.df['booking_confirmed'].mean()*100:.1f}%)")
        report.append(f"Average duration: {self.df['duration_seconds'].mean():.1f} seconds")
        report.append(f"Total messages exchanged: {self.df['total_messages'].sum()}")
        report.append(f"Conversations with errors: {(self.df['errors'] > 0).sum()}")
        report.append("")
        
        # By persona analysis
        report.append("👥 ANALYSIS BY PERSONA TYPE")
        report.append("-"*40)
        
        for persona_type in self.df['persona_type'].unique():
            persona_data = self.df[self.df['persona_type'] == persona_type]
            report.append(f"\n{persona_type.upper()}")
            report.append(f"  • Conversations: {len(persona_data)}")
            report.append(f"  • Booking rate: {persona_data['booking_confirmed'].mean()*100:.1f}%")
            report.append(f"  • Avg messages: {persona_data['total_messages'].mean():.1f}")
            report.append(f"  • Avg duration: {persona_data['duration_seconds'].mean():.1f}s")
            report.append(f"  • Error rate: {(persona_data['errors'] > 0).mean()*100:.1f}%")
        
        return "\n".join(report)

class ConversationExporter:
    """Export conversations in multiple formats"""
    
    def __init__(self, results: List[ConversationResult]):
        self.results = results
        
    def export_to_html(self, filepath: str = "conversations.html"):
        """Export conversations to interactive HTML"""
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Wandero Client Simulation Results</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background-color: #2c3e50; color: white; padding: 20px; border-radius: 10px; }
        .conversation { background-color: white; margin: 20px 0; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .metadata { background-color: #ecf0f1; padding: 10px; border-radius: 5px; margin-bottom: 20px; }
        .message { margin: 10px 0; padding: 15px; border-radius: 5px; }
        .client { background-color: #e3f2fd; border-left: 4px solid #2196f3; }
        .wandero { background-color: #f3e5f5; border-left: 4px solid #9c27b0; }
        .timestamp { color: #666; font-size: 0.9em; }
        .success { color: #27ae60; font-weight: bold; }
        .failed { color: #e74c3c; font-weight: bold; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }
        .stat-card { background-color: white; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .stat-number { font-size: 2em; font-weight: bold; color: #3498db; }
        .tabs { display: flex; gap: 10px; margin: 20px 0; }
        .tab { padding: 10px 20px; background-color: #bdc3c7; cursor: pointer; border-radius: 5px; }
        .tab.active { background-color: #3498db; color: white; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
    </style>
    <script>
        function showTab(tabId) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.getElementById(tabId + '-tab').classList.add('active');
            document.getElementById(tabId + '-content').classList.add('active');
        }
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Wandero Client Simulation Results</h1>
            <p>Generated: {timestamp}</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{total_conversations}</div>
                <div>Total Conversations</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{successful_bookings}</div>
                <div>Successful Bookings</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{avg_duration:.1f}s</div>
                <div>Average Duration</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{total_messages}</div>
                <div>Total Messages</div>
            </div>
        </div>
        
        <div class="tabs">
"""
        
        # Create tabs for each conversation
        for idx, result in enumerate(self.results):
            active = "active" if idx == 0 else ""
            html_content += f'<div id="conv{idx}-tab" class="tab {active}" onclick="showTab(\'conv{idx}\')">{result.persona_name}</div>\n'
        
        html_content += "</div>\n"
        
        # Create content for each conversation
        for idx, result in enumerate(self.results):
            active = "active" if idx == 0 else ""
            status_class = "success" if result.booking_confirmed else "failed"
            status_text = "✅ Booking Confirmed" if result.booking_confirmed else "❌ Not Completed"
            
            html_content += f"""
        <div id="conv{idx}-content" class="tab-content {active}">
            <div class="conversation">
                <div class="metadata">
                    <h2>{result.persona_name} ({result.persona_type})</h2>
                    <p><strong>Thread ID:</strong> {result.thread_id}</p>
                    <p><strong>Duration:</strong> {result.total_duration_seconds:.1f} seconds</p>
                    <p><strong>Status:</strong> <span class="{status_class}">{status_text}</span></p>
                    <p><strong>Total Messages:</strong> {result.total_messages}</p>
                </div>
"""
            
            for msg in result.messages:
                role_class = "client" if msg['role'] == 'client' else 'wandero'
                timestamp = msg.get('timestamp', 'Unknown time')
                content = html.escape(msg['content']).replace('\n', '<br>')
                
                html_content += f"""
                <div class="message {role_class}">
                    <div class="timestamp">{timestamp} - {msg['role'].upper()}</div>
                    <div>{content}</div>
                </div>
"""
            
            if result.errors:
                html_content += "<h3>Errors:</h3><ul>"
                for error in result.errors:
                    html_content += f"<li>{html.escape(error)}</li>"
                html_content += "</ul>"
            
            html_content += """
            </div>
        </div>
"""
        
        # Add summary statistics
        total_msgs = sum(r.total_messages for r in self.results)
        avg_duration = sum(r.total_duration_seconds for r in self.results) / len(self.results) if self.results else 0
        successful = sum(1 for r in self.results if r.booking_confirmed)
        
        html_content = html_content.format(
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            total_conversations=len(self.results),
            successful_bookings=successful,
            avg_duration=avg_duration,
            total_messages=total_msgs
        )
        
        html_content += """
    </div>
</body>
</html>
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"🌐 Conversations exported to {filepath}")

# Main execution logic with test options
async def run_two_personas_test():
    """Run test with two selected personas"""
    print("\n" + "="*100)
    print("🚀 WANDERO CLIENT SIMULATION - TWO PERSONAS TEST")
    print("="*100)
    
    # Select two personas for quick testing
    persona_types = ["worried_parent", "adventure_couple"]
    
    print(f"\n👥 Testing with 2 personas:")
    for pt in persona_types:
        persona = PersonaLibrary.get_persona(pt)
        print(f"   - {persona['name']} ({pt})")
    
    # Initialize engine
    engine = ParallelConversationEngine(max_workers=2)
    
    # Run parallel conversations
    print(f"\n🔄 Starting parallel conversations...")
    start_time = datetime.now()
    
    results = await engine.run_parallel_conversations(persona_types)
    
    end_time = datetime.now()
    total_duration = (end_time - start_time).total_seconds()
    
    print(f"\n✅ All conversations completed in {total_duration:.1f} seconds")
    
    # Generate analytics
    print(f"\n📊 Generating analytics...")
    analytics = ConversationAnalytics(results)
    print(analytics.generate_summary_report())
    
    # Export conversations
    print(f"\n💾 Exporting conversations...")
    exporter = ConversationExporter(results)
    exporter.export_to_html("two_personas_test.html")
    
    print(f"\n🎉 TWO PERSONAS TEST COMPLETE!")
    print(f"Total execution time: {total_duration:.1f} seconds")
    print(f"📁 Output file: two_personas_test.html")

async def run_all_personas_test():
    """Run test with all available personas"""
    print("\n" + "="*100)
    print("🚀 WANDERO CLIENT SIMULATION - ALL PERSONAS TEST")
    print("="*100)
    
    # Get all persona types
    all_personas = PersonaLibrary.get_all_personas()
    persona_types = list(all_personas.keys())
    
    print(f"\n👥 Testing with {len(persona_types)} personas:")
    for pt in persona_types:
        persona = PersonaLibrary.get_persona(pt)
        print(f"   - {persona['name']} ({pt})")
    
    # Initialize engine
    engine = ParallelConversationEngine(max_workers=3)
    
    # Run parallel conversations
    print(f"\n🔄 Starting parallel conversations...")
    start_time = datetime.now()
    
    results = await engine.run_parallel_conversations(persona_types)
    
    end_time = datetime.now()
    total_duration = (end_time - start_time).total_seconds()
    
    print(f"\n✅ All conversations completed in {total_duration:.1f} seconds")
    
    # Generate analytics
    print(f"\n📊 Generating analytics...")
    analytics = ConversationAnalytics(results)
    print(analytics.generate_summary_report())
    
    # Export conversations
    print(f"\n💾 Exporting conversations...")
    exporter = ConversationExporter(results)
    exporter.export_to_html("all_personas_test.html")
    
    print(f"\n🎉 ALL PERSONAS TEST COMPLETE!")
    print(f"Total execution time: {total_duration:.1f} seconds")
    print(f"📁 Output file: all_personas_test.html")

def display_menu():
    """Display interactive menu for test selection"""
    print("\n" + "="*60)
    print("🤖 WANDERO CLIENT SIMULATION SYSTEM")
    print("="*60)
    print("\nSelect test option:")
    print("1. Two Personas Test (Quick test with 2 selected personas)")
    print("2. All Personas Test (Comprehensive test with all 5 personas)")
    print("3. Exit")
    print("-"*60)

async def main():
    """Main execution function with interactive menu"""
    while True:
        display_menu()
        
        try:
            choice = input("\nEnter your choice (1-3): ").strip()
            
            if choice == "1":
                await run_two_personas_test()
                input("\nPress Enter to continue...")
                
            elif choice == "2":
                await run_all_personas_test()
                input("\nPress Enter to continue...")
                
            elif choice == "3":
                print("\n👋 Thank you for using Wandero Client Simulation System!")
                break
                
            else:
                print("\n❌ Invalid choice. Please enter 1, 2, or 3.")
                
        except KeyboardInterrupt:
            print("\n\n⚠️ Operation cancelled by user.")
            break
        except Exception as e:
            print(f"\n❌ An error occurred: {e}")
            import traceback
            traceback.print_exc()
            input("\nPress Enter to continue...")

if __name__ == "__main__":
    # For automated testing, you can uncomment one of these lines:
    # asyncio.run(run_two_personas_test())
    # asyncio.run(run_all_personas_test())
    
    # For interactive menu:
    asyncio.run(main())



