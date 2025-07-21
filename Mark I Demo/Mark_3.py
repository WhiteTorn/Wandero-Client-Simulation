from typing import Annotated, TypedDict, List, Dict, Literal
import operator
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from IPython.display import Image, display
from time import sleep
from datetime import datetime

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

class ClientState(TypedDict):
    """Everything Our Client Remembers"""
    messages: Annotated[List[Dict[str, str]], operator.add]
    phase: Literal[
        "initial_inquiry",
        "providing_details",
        "reviewing_proposal", 
        "confirming"
    ]
    provided_info: Dict[str, bool]
    persona_name: str
    persona_traits: List[str]
    forgotten_details: List[str]

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model = "gemini-2.0-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.7 # Naturality
)

def safe_llm_invoke(prompt: str, delay_seconds: int = 5, node_name: str = "unknown") -> str:
    """Safely invoke LLM with comprehensive error handling and tracking"""
    print(f"🤖 [{node_name}] Making LLM request...")
    print(f"⏰ [{node_name}] Waiting {delay_seconds} seconds before API call...")
    sleep(delay_seconds)
    
    try:
        print(f"📡 [{node_name}] Sending request to Gemini API...")
        response = llm.invoke(prompt).content
        print(f"✅ [{node_name}] API request successful!")
        print(f"📝 [{node_name}] Response preview: {response}...")
        
        # Additional delay after successful request
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
        
        # For other errors, return fallback
        print(f"🎭 [{node_name}] Using fallback response due to unexpected error...")
        return "Thank you for your response. I'm interested in planning our trip."

def print_state_debug(state: ClientState, node_name: str):
    """Print detailed state information for debugging"""
    print(f"\n🔍 [{node_name}] STATE DEBUG:")
    print(f"   📍 Phase: {state.get('phase', 'unknown')}")
    print(f"   👤 Persona: {state.get('persona_name', 'unknown')}")
    print(f"   📊 Messages count: {len(state.get('messages', []))}")
    print(f"   ✅ Provided info: {state.get('provided_info', {})}")
    print(f"   🤔 Forgotten details: {state.get('forgotten_details', [])}")
    
    messages = state.get('messages', [])
    if messages:
        print(f"   💬 Recent messages:")
        for i, msg in enumerate(messages[-2:]):  # Show last 2 messages
            role_emoji = "👤" if msg['role'] == 'client' else "🏢" if msg['role'] == 'wandero' else "⚙️"
            print(f"      {role_emoji} {msg['role']}: {msg['content']}...")

def initial_inquiry_node(state: ClientState) -> Dict:
    """Generate the first email to Wandero"""
    
    print(f"\n{'='*50}")
    print(f"🚀 INITIAL INQUIRY NODE STARTED")
    print(f"{'='*50}")
    
    print_state_debug(state, "INITIAL_INQUIRY")
    
    print(f"📝 Creating initial inquiry prompt...")
    prompt = f"""You are {state['persona_name']}, a parent planning a family trip.
Write a natural email asking about tours to {state.get('destination', 'Chile')}.
BE REALISTIC: Don't include all details. Forget to mention:
- Exact number of people
- Children's ages
- Specific dates

Keep it conversational, 2-3 paragraphs."""
    
    print(f"📋 Prompt created: {len(prompt)} characters")
    
    response = safe_llm_invoke(prompt, delay_seconds=6, node_name="INITIAL_INQUIRY")
    
    result = {
        "messages": [{"role": "client", "content": response}],
        "phase": "providing_details",
        "provided_info": {"destination": True, "dates": False, "family_size": False}
    }
    
    print(f"📤 Initial inquiry generated successfully")
    print(f"🔄 Phase updated to: providing_details")
    print(f"{'='*50}")
    
    return result

def provide_details_node(state: ClientState) -> Dict:
    """Provide requested information (but forget something!)"""
    
    print(f"\n{'='*50}")
    print(f"📋 PROVIDE DETAILS NODE STARTED") 
    print(f"{'='*50}")
    
    print_state_debug(state, "PROVIDE_DETAILS")
    
    print(f"🔍 Searching for last Wandero message...")
    last_wandero_msg = ""
    for msg in reversed(state["messages"]):
        if msg["role"] == "wandero":
            last_wandero_msg = msg["content"]
            print(f"📨 Found Wandero message: {last_wandero_msg}...")
            break
    
    if not last_wandero_msg:
        print(f"⚠️ No Wandero message found, using generic response")
        last_wandero_msg = "Please provide more details about your trip"

    print(f"📝 Creating detailed response prompt...")
    prompt = f"""You are {state['persona_name']}. 
Wandero asked: "{last_wandero_msg}"

Provide the information they asked for:
- Family of 4 (2 adults, 2 children)
- Dates: July 15-22, 2024
- Budget: $4000-6000

BUT FORGET to mention your children's ages. This is important - humans forget things!"""

    response = safe_llm_invoke(prompt, delay_seconds=7, node_name="PROVIDE_DETAILS")
    
    result = {
        "messages": [{"role": "client", "content": response}],
        "provided_info": {
            **state["provided_info"],
            "dates": True,
            "family_size": True,
            "ages": False  # Forgot this!
        },
        "forgotten_details": ["children_ages"]
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
    print(f"🔍 Checking forgotten details: {forgotten_details}")
    
    if "children_ages" in forgotten_details:
        print(f"💡 Found forgotten detail: children_ages")
        print(f"📝 Creating correction email prompt...")
        
        prompt = f"""You are {state['persona_name']}.
Write a SHORT follow-up email saying:
"Oh, I forgot to mention - my children are 12 and 8 years old"

Make it natural and apologetic."""

        response = safe_llm_invoke(prompt, delay_seconds=5, node_name="SEND_CORRECTION")
        
        result = {
            "messages": [
                {"role": "system", "content": "[Sent 5 minutes later]"},
                {"role": "client", "content": response}
            ],
            "provided_info": {**state["provided_info"], "ages": True},
            "forgotten_details": []  # Clear the forgotten items
        }
        
        print(f"📤 Correction email sent successfully")
        print(f"✅ Updated provided_info with ages: True")
        print(f"🧹 Cleared forgotten_details")
        print(f"{'='*50}")
        
        return result
    
    print(f"ℹ️ No corrections needed")
    print(f"{'='*50}")
    return {}  # if nothing forgotten, no updates

print(f"\n🏗️ BUILDING LANGGRAPH...")
print(f"⚙️ Creating StateGraph...")

graph_builder = StateGraph(ClientState)

print(f"📦 Adding nodes to graph...")
graph_builder.add_node("initial_inquiry", initial_inquiry_node)
graph_builder.add_node("provide_details", provide_details_node) 
graph_builder.add_node("send_correction", send_correction_node)

print(f"🚪 Setting entry point...")
graph_builder.set_entry_point("initial_inquiry")

print(f"🔗 Adding edges...")
# After Initial inquiry should be details.
graph_builder.add_edge("initial_inquiry", "provide_details")

def needs_correction(state: ClientState) -> str:
    """Decide if we need to send a correction"""
    forgotten = state.get("forgotten_details", [])
    print(f"🤔 [DECISION] Checking if correction needed...")
    print(f"🤔 [DECISION] Forgotten details: {forgotten}")
    
    if forgotten:
        print(f"✅ [DECISION] Correction needed -> send_correction")
        return "send_correction"
    
    print(f"🏁 [DECISION] No correction needed -> end")
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

print(f"🔧 Compiling graph...")
client_graph = graph_builder.compile()
print(f"✅ Graph compiled successfully!")

try:
    from IPython.display import Image, display
    print(f"🖼️ Displaying graph visualization...")
    display(Image(client_graph.get_graph().draw_mermaid_png()))
except Exception as e:
    print(f"⚠️ Could not display graph visualization: {e}")

class MockWandero:
    """Simple rule-based Wandero for testing"""
    
    def respond(self, client_message: str, round_num: int = 0) -> str:
        print(f"🏢 [WANDERO] Processing client message (Round {round_num})...")
        print(f"🏢 [WANDERO] Message preview: {client_message}...")
        
        msg_lower = client_message.lower()
        
        if "trip" in msg_lower and "chile" in msg_lower:
            response = """Thank you for your interest! To create a custom itinerary, 
            please provide:
            - Number of travelers (adults and children with ages)
            - Travel dates
            - Budget range
            - Any special requirements"""
            
        elif "july" in msg_lower and "4" in msg_lower:
            response = """Perfect! I'll create a family package for 4 people 
            traveling July 15-22. Just to confirm - what are the ages 
            of your children? This helps us plan age-appropriate activities."""
            
        else:
            response = "Thank you for the information!"
        
        print(f"🏢 [WANDERO] Response generated: {response}...")
        return response
    
def run_simulation():
    """Run a complete conversation simulation"""
    
    print(f"\n{'='*80}")
    print(f"🚀 WANDERO CLIENT SIMULATION STARTED")
    print(f"⏰ Start time: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*80}")
    
    # Initialize
    print(f"🏗️ INITIALIZATION PHASE")
    print(f"-" * 40)
    
    print(f"🤖 Creating Wandero mock...")
    wandero = MockWandero()
    print(f"✅ Wandero mock created")
    
    print(f"👤 Creating persona...")
    persona = create_persona()
    print(f"✅ Persona created: {persona['name']}")
    
    # Create initial state
    print(f"🌱 Creating initial state...")
    initial_state = {
        "messages": [],
        "phase": "initial_inquiry",
        "provided_info": {},
        "persona_name": persona["name"],
        "persona_traits": persona["traits"],
        "forgotten_details": []
    }
    print(f"✅ Initial state created")
    
    print(f"\n🔍 INITIAL STATE DEBUG:")
    print_state_debug(initial_state, "INITIALIZATION")
    
    # Run the client graph
    print(f"\n{'='*80}")
    print(f"🚀 GRAPH EXECUTION PHASE")
    print(f"{'='*80}")
    
    print(f"⚡ Invoking client graph...")
    try:
        final_state = client_graph.invoke(initial_state)
        print(f"✅ Graph execution completed successfully!")
        
    except Exception as e:
        print(f"❌ Graph execution failed: {e}")
        print(f"💥 Simulation terminated")
        return
    
    print(f"\n🔍 FINAL STATE DEBUG:")
    print_state_debug(final_state, "FINAL")
    
    # Show the conversation
    print(f"\n{'='*80}")
    print(f"💬 CONVERSATION DISPLAY")
    print(f"{'='*80}")
    
    round_num = 0
    for i, msg in enumerate(final_state["messages"]):
        if msg["role"] == "client":
            round_num += 1
            print(f"\n📧 CLIENT EMAIL #{round_num}")
            print(f"📤 From: {persona['name']}")
            print(f"🕐 Time: {datetime.now().strftime('%H:%M:%S')}")
            print(f"-" * 60)
            print(msg['content'])
            print(f"-" * 60)
            
            # Get Wandero's response
            print(f"⏰ Wandero processing... (simulating 3 second delay)")
            sleep(3)
            
            wandero_response = wandero.respond(msg["content"], round_num)
            
            print(f"\n🏢 WANDERO RESPONSE #{round_num}")
            print(f"📤 From: Maria Rodriguez (Chile Adventures)")
            print(f"🕐 Time: {datetime.now().strftime('%H:%M:%S')}")
            print(f"-" * 60)
            print(wandero_response)
            print(f"-" * 60)
            
        elif msg["role"] == "system":
            print(f"\n⚙️ SYSTEM NOTE: {msg['content']}")
    
    # Final summary
    print(f"\n{'='*80}")
    print(f"📊 SIMULATION SUMMARY")
    print(f"{'='*80}")
    
    client_msgs = len([m for m in final_state["messages"] if m["role"] == "client"])
    system_msgs = len([m for m in final_state["messages"] if m["role"] == "system"])
    
    print(f"📧 Total client emails: {client_msgs}")
    print(f"⚙️ Total system messages: {system_msgs}")
    print(f"💬 Total messages: {len(final_state['messages'])}")
    print(f"📍 Final phase: {final_state.get('phase', 'unknown')}")
    print(f"✅ Information provided: {final_state.get('provided_info', {})}")
    print(f"⏰ End time: {datetime.now().strftime('%H:%M:%S')}")
    print(f"\n🎉 SIMULATION COMPLETED SUCCESSFULLY!")

# Run it!
if __name__ == "__main__":
    try:
        run_simulation()
    except Exception as e:
        print(f"\n💥 FATAL ERROR: {e}")
        print(f"❌ Simulation failed completely")