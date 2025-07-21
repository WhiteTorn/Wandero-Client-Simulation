from typing import TypedDict, List, Dict, Literal, Annotated, Optional, Any
from datetime import datetime, timedelta
import operator
import os
import re
import random
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from IPython.display import Image, display
from time import sleep
from langgraph.checkpoint.memory import MemorySaver 

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

# Mock Wandero (kept from original - simplified)
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

# Enhanced graph with proposal handling
def build_enhanced_graph():
    """Build graph with stateful Wandero integration"""
    print(f"\n🏗️ BUILDING ENHANCED GRAPH WITH STATEFUL WANDERO...")
    
    graph_builder = StateGraph(ClientState)
    
    # Add all nodes
    graph_builder.add_node("initial_inquiry", initial_inquiry_node)
    graph_builder.add_node("provide_details", provide_details_node)
    graph_builder.add_node("send_correction", send_correction_node)
    graph_builder.add_node("review_proposal", review_proposal_node)
    graph_builder.add_node("confirm_booking", confirm_booking_node)
    
    # Set entry point
    graph_builder.set_entry_point("initial_inquiry")
    
    # Define flow
    graph_builder.add_edge("initial_inquiry", "provide_details")
    
    def decide_after_details(state: ClientState) -> str:
        """Decide next step after providing details"""
        forgotten = state.get("forgotten_details", [])
        if forgotten:
            return "send_correction"
        return "review_proposal"
    
    graph_builder.add_conditional_edges(
        "provide_details",
        decide_after_details,
        {
            "send_correction": "send_correction",
            "review_proposal": "review_proposal"
        }
    )
    
    graph_builder.add_edge("send_correction", "review_proposal")
    
    def decide_after_review(state: ClientState) -> str:
        """Decide next step after reviewing proposal"""
        phase = state.get("phase", "")
        if phase == "completed":
            return "end"
        elif phase == "negotiating":
            return "confirm_booking"
        return "end"
    
    graph_builder.add_conditional_edges(
        "review_proposal",
        decide_after_review,
        {
            "confirm_booking": "confirm_booking",
            "end": END
        }
    )
    
    graph_builder.add_edge("confirm_booking", END)
    
    print(f"✅ Enhanced graph built successfully!")
    return graph_builder.compile(checkpointer=memory)

# Enhanced simulation with stateful Wandero
def run_enhanced_simulation():
    """Run simulation with stateful Wandero"""
    print(f"\n{'='*80}")
    print(f"🚀 ENHANCED WANDERO CLIENT SIMULATION WITH STATEFUL BOT")
    print(f"⏰ Start time: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*80}")
    
    # Initialize
    wandero = StatefulWandero()
    persona = create_persona()
    
    # Create thread config
    thread_id = f"enhanced_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    config = {"configurable": {"thread_id": thread_id}}
    
    # Initial state
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
    
    # Build and run graph
    client_graph = build_enhanced_graph()
    
    print(f"🧵 Thread ID: {thread_id}")
    print(f"👤 Client: {persona['name']}")
    print(f"🏢 Agent: {wandero.company_info['agent']} ({wandero.company_info['name']})")
    print(f"\n" + "="*80 + "\n")
    
    try:
        # Run the graph to get client messages
        client_state = client_graph.invoke(initial_state, config)
        
        # Process conversation with stateful Wandero
        for msg in client_state["messages"]:
            if msg["role"] == "client":
                # Display client message
                print(f"📧 CLIENT: {persona['name']}")
                print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
                print("-" * 60)
                print(msg['content'])
                print("-" * 60)
                
                # Get Wandero's response
                print(f"\n⏳ Wandero processing...")
                sleep(2)
                
                wandero_response = wandero.process_email(msg['content'], client_state)
                
                print(f"\n🏢 WANDERO: {wandero.company_info['agent']}")
                print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
                print(f"Phase: {wandero.state['conversation_phase']}")
                print("-" * 60)
                print(wandero_response)
                print("-" * 60)
                print("\n" + "="*80 + "\n")
                
                # Add Wandero response to state for next iteration
                client_state["messages"].append({"role": "wandero", "content": wandero_response})
                
                # If we have a proposal, continue the conversation
                if wandero.state["conversation_phase"] == "proposal_sent":
                    # Update client state to trigger proposal review
                    client_state["phase"] = "reviewing_proposal"
                elif wandero.state["conversation_phase"] == "booking_confirmed":
                    client_state["phase"] = "completed"
                
            elif msg["role"] == "system":
                print(f"⚙️ SYSTEM: {msg['content']}\n")
        
        # Final summary
        print(f"\n{'='*80}")
        print(f"📊 SIMULATION SUMMARY")
        print(f"{'='*80}")
        print(f"🏢 WANDERO STATE:")
        print(f"  - Conversation phase: {wandero.state['conversation_phase']}")
        print(f"  - Interactions: {wandero.state['interaction_count']}")
        print(f"  - Collected info: {list(wandero.state['collected_info'].keys())}")
        print(f"  - Special requirements: {wandero.state['special_requirements']}")
        
        print(f"\n👤 CLIENT STATE:")
        print(f"  - Phase: {client_state['phase']}")
        print(f"  - Mood: {client_state['mood']}")
        print(f"  - Emails sent: {client_state['metadata']['email_count']}")
        print(f"  - Concerns raised: {client_state.get('concerns_raised', [])}")
        
        print(f"\n⏰ End time: {datetime.now().strftime('%H:%M:%S')}")
        print(f"\n🎉 ENHANCED SIMULATION COMPLETED!")
        
    except Exception as e:
        print(f"❌ Enhanced simulation failed: {e}")
        import traceback
        traceback.print_exc()

# Main execution
if __name__ == "__main__":
    print(f"\n🎯 WANDERO CLIENT SIMULATION SYSTEM")
    print(f"Choose simulation type:")
    print(f"1. Original (Simple Wandero)")
    print(f"2. Memory-Aware (Simple Wandero)")  
    print(f"3. Enhanced (Stateful Wandero)")
    
    # For automated demo, run enhanced
    print(f"\n📌 Running Enhanced Simulation with Stateful Wandero...")
    
    try:
        run_enhanced_simulation()
    except Exception as e:
        print(f"\n💥 FATAL ERROR: {e}")
        print(f"❌ Simulation failed")