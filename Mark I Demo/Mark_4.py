from typing import TypedDict, List, Dict, Literal, Annotated, Optional
from datetime import datetime, timedelta
import operator
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from IPython.display import Image, display
from time import sleep
from langgraph.checkpoint.memory import MemorySaver 
import random

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
    persona_traits: List[str]
    forgotten_details: List[str]
    conversation_memory: List[str]
    questions_asked: List[str]
    concerns_raised: List[str]
    metadata: ConversationMetadata
    mood: Literal["excited", "cautious", "frustrated", "satisfied"]

# Persona creation
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

# New memory-aware nodes
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

def memory_aware_response_node(state: ClientState) -> Dict:
    """Generate responses using conversation memory"""
    print(f"\n{'='*50}")
    print(f"💭 MEMORY-AWARE RESPONSE NODE STARTED")
    print(f"{'='*50}")
    
    memory_context = "\n".join([
        f"- {memory}" for memory in state.get("conversation_memory", [])
    ])
    
    mood_instruction = {
        "excited": "Be enthusiastic and eager",
        "cautious": "Be careful and ask clarifying questions",
        "frustrated": "Be slightly impatient but still polite",
        "satisfied": "Be happy and ready to proceed"
    }
    
    current_mood = state.get("mood", "excited")
    
    prompt = f"""You are {state['persona_name']} continuing an email conversation.
    
Your mood: {current_mood} - {mood_instruction.get(current_mood, '')}

Previous conversation points:
{memory_context}

Questions you've asked before: {', '.join(state.get('questions_asked', []))}

Based on the context, write a natural follow-up email. If you've asked questions 
before that weren't answered, politely mention this."""

    response = safe_llm_invoke(prompt, 7, "MEMORY_AWARE_RESPONSE")
    
    result = {
        "messages": [{"role": "client", "content": response}],
        "metadata": {
            **state.get("metadata", {}),
            "last_updated": datetime.now().isoformat(),
            "email_count": state.get("metadata", {}).get("email_count", 0) + 1
        }
    }
    
    print(f"📤 Memory-aware response generated")
    print(f"{'='*50}")
    
    return result

def determine_response_time_node(state: ClientState) -> Dict:
    """Decide when the client will respond"""
    print(f"\n{'='*50}")
    print(f"⏰ DETERMINE RESPONSE TIME NODE STARTED")
    print(f"{'='*50}")
    
    current_time = datetime.now()
    mood = state.get("mood", "excited")
    
    # Response delays based on mood
    if mood == "excited":
        delay_minutes = random.randint(5, 30)
    elif mood == "frustrated":
        delay_minutes = random.randint(1, 10)
    else:
        delay_minutes = random.randint(30, 240)
    
    # Add business hours logic
    response_time = current_time + timedelta(minutes=delay_minutes)
    if response_time.hour > 18:
        response_time = response_time.replace(
            hour=9, 
            minute=random.randint(0, 30),
            day=response_time.day + 1
        )
    
    print(f"📅 Client will respond at: {response_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"⏱️ Delay: {delay_minutes} minutes (mood: {mood})")
    print(f"{'='*50}")
    
    return {
        "messages": [{
            "role": "system",
            "content": f"[Client will respond at {response_time.strftime('%Y-%m-%d %H:%M')}]"
        }]
    }

# Graph builders
def build_original_graph():
    """Build the original simple graph"""
    print(f"\n🏗️ BUILDING ORIGINAL GRAPH...")
    
    graph_builder = StateGraph(ClientState)
    
    # Add nodes
    graph_builder.add_node("initial_inquiry", initial_inquiry_node)
    graph_builder.add_node("provide_details", provide_details_node) 
    graph_builder.add_node("send_correction", send_correction_node)
    
    # Set entry point
    graph_builder.set_entry_point("initial_inquiry")
    
    # Add edges
    graph_builder.add_edge("initial_inquiry", "provide_details")
    
    def needs_correction(state: ClientState) -> str:
        forgotten = state.get("forgotten_details", [])
        if forgotten:
            return "send_correction"
        return "end"
    
    graph_builder.add_conditional_edges(
        "provide_details",
        needs_correction,
        {
            "send_correction": "send_correction",
            "end": END
        }
    )
    
    graph_builder.add_edge("send_correction", END)
    
    print(f"✅ Original graph built successfully!")
    return graph_builder.compile()

def create_memory_graph():
    """Create a graph with memory capabilities"""
    print(f"\n🏗️ BUILDING MEMORY-AWARE GRAPH...")
    
    builder = StateGraph(ClientState)
    
    # Add all nodes
    builder.add_node("initial_inquiry", initial_inquiry_node)
    builder.add_node("analyze_conversation", analyze_conversation_node)
    builder.add_node("determine_response_time", determine_response_time_node)
    builder.add_node("generate_response", memory_aware_response_node)
    builder.add_node("provide_details", provide_details_node)
    builder.add_node("send_correction", send_correction_node)
    
    # Set entry point
    builder.set_entry_point("initial_inquiry")
    
    # Define the flow
    builder.add_edge("initial_inquiry", "analyze_conversation")
    builder.add_edge("analyze_conversation", "determine_response_time")
    builder.add_edge("determine_response_time", "provide_details")
    
    def needs_correction_or_continue(state: ClientState) -> str:
        forgotten = state.get("forgotten_details", [])
        if forgotten:
            return "send_correction"
        
        if state.get("phase") == "completed":
            return "end"
        
        email_count = state.get("metadata", {}).get("email_count", 0)
        if email_count > 10:
            return "end"
        
        return "generate_response"
    
    builder.add_conditional_edges(
        "provide_details",
        needs_correction_or_continue,
        {
            "send_correction": "send_correction",
            "generate_response": "generate_response",
            "end": END
        }
    )
    
    builder.add_edge("send_correction", "generate_response")
    builder.add_edge("generate_response", END)
    
    print(f"✅ Memory-aware graph built successfully!")
    return builder.compile(checkpointer=memory)

# Mock Wandero (kept from original)
class MockWandero:
    """Simple rule-based Wandero for testing"""
    
    def respond(self, client_message: str, round_num: int = 0) -> str:
        print(f"🏢 [WANDERO] Processing client message (Round {round_num})...")
        
        msg_lower = client_message.lower()
        
        if "trip" in msg_lower and "chile" in msg_lower:
            response = """Thank you for your interest! To create a custom itinerary, 
            please provide:
            - Number of travelers (adults and children with ages)
            - Travel dates
            - Budget range
            - Any special requirements"""
            
        elif "july" in msg_lower and ("4" in msg_lower or "family" in msg_lower):
            response = """Perfect! I'll create a family package for 4 people 
            traveling July 15-22. Just to confirm - what are the ages 
            of your children? This helps us plan age-appropriate activities."""
            
        elif "12" in msg_lower and "8" in msg_lower:
            response = """Excellent! With children aged 12 and 8, I recommend our 
            'Family Adventure Package' which includes:
            - Santiago city tour with interactive museums
            - Valparaíso coastal excursion
            - Mild adventure activities suitable for children
            - All meals with allergy accommodations
            Total: $5,200 for your family. Shall I send the detailed itinerary?"""
            
        else:
            response = "Thank you for the information! Let me check what else I need."
        
        print(f"🏢 [WANDERO] Response generated")
        return response

# Main simulation functions
def run_original_simulation():
    """Run the original simple simulation"""
    print(f"\n{'='*80}")
    print(f"🚀 ORIGINAL WANDERO CLIENT SIMULATION")
    print(f"⏰ Start time: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*80}")
    
    # Initialize
    wandero = MockWandero()
    persona = create_persona()
    
    # Create initial state with minimal fields
    initial_state = {
        "messages": [],
        "phase": "initial_inquiry",
        "provided_info": {},
        "persona_name": persona["name"],
        "persona_traits": persona["traits"],
        "forgotten_details": [],
        "conversation_memory": [],
        "questions_asked": [],
        "concerns_raised": [],
        "mood": "excited",
        "metadata": {
            "thread_id": f"simple_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "started_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "email_count": 0,
            "current_topic": "Chile family vacation"
        }
    }
    
    # Build and run graph
    client_graph = build_original_graph()
    
    try:
        final_state = client_graph.invoke(initial_state)
        print(f"✅ Graph execution completed successfully!")
    except Exception as e:
        print(f"❌ Graph execution failed: {e}")
        return
    
    # Display conversation
    print(f"\n{'='*80}")
    print(f"💬 CONVERSATION DISPLAY")
    print(f"{'='*80}")
    
    round_num = 0
    for msg in final_state["messages"]:
        if msg["role"] == "client":
            round_num += 1
            print(f"\n📧 CLIENT EMAIL #{round_num}")
            print(f"From: {persona['name']}")
            print(f"-" * 60)
            print(msg['content'])
            print(f"-" * 60)
            
            # Get Wandero's response
            sleep(2)
            wandero_response = wandero.respond(msg["content"], round_num)
            
            print(f"\n🏢 WANDERO RESPONSE #{round_num}")
            print(f"From: Maria Rodriguez (Chile Adventures)")
            print(f"-" * 60)
            print(wandero_response)
            print(f"-" * 60)
            
            # Add Wandero response to state for next iteration
            final_state["messages"].append({"role": "wandero", "content": wandero_response})
            
        elif msg["role"] == "system":
            print(f"\n⚙️ SYSTEM: {msg['content']}")
    
    # Summary
    print(f"\n{'='*80}")
    print(f"📊 SIMULATION SUMMARY")
    print(f"{'='*80}")
    print(f"📧 Total client emails: {sum(1 for m in final_state['messages'] if m['role'] == 'client')}")
    print(f"💬 Total messages: {len(final_state['messages'])}")
    print(f"✅ Information provided: {final_state.get('provided_info', {})}")
    print(f"\n🎉 SIMULATION COMPLETED!")

def run_memory_simulation():
    """Run simulation with memory features"""
    print(f"\n{'='*80}")
    print(f"🚀 MEMORY-AWARE WANDERO CLIENT SIMULATION")
    print(f"⏰ Start time: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*80}")
    
    # Create memory graph
    graph = create_memory_graph()
    
    # Create thread config
    thread_id = f"memory_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    config = {"configurable": {"thread_id": thread_id}}
    
    # Initial state
    persona = create_persona()
    initial_state = {
        "messages": [],
        "phase": "initial_inquiry",
        "provided_info": {},
        "persona_name": persona["name"],
        "persona_traits": persona["traits"],
        "forgotten_details": [],
        "conversation_memory": [],
        "questions_asked": [],
        "concerns_raised": [],
        "mood": "excited",
        "metadata": {
            "thread_id": thread_id,
            "started_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "email_count": 0,
            "current_topic": "Chile family vacation"
        }
    }
    
    print(f"🧵 Thread ID: {thread_id}")
    
    # Run simulation
    try:
        result = graph.invoke(initial_state, config)
        print(f"\n✅ Memory simulation completed!")
        
        # Show results
        print(f"\n📊 Final State:")
        print(f"  - Mood: {result.get('mood')}")
        print(f"  - Emails sent: {result['metadata']['email_count']}")
        print(f"  - Memory points: {len(result.get('conversation_memory', []))}")
        
        if result.get('conversation_memory'):
            print(f"\n🧠 Conversation Memory:")
            for memory in result['conversation_memory']:
                print(f"  - {memory}")
                
    except Exception as e:
        print(f"❌ Memory simulation failed: {e}")

# Main execution
if __name__ == "__main__":
    print(f"\n🎯 WANDERO CLIENT SIMULATION SYSTEM")
    
    # For automated execution, run the original simulation
    print(f"\nRunning Memory Simulation...")
    
    try:
        run_memory_simulation()
        
    except Exception as e:
        print(f"\n💥 FATAL ERROR: {e}")
        print(f"❌ Simulation failed")