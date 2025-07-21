from typing import TypedDict, List, Dict, Literal, Optional
import random
from datetime import datetime, timedelta

class WanderoState(TypedDict):
    """Simple but complete wandero state"""
    # Identity  
    company_name: str
    company_data: Dict  # Full company dict from companies.py
    agent_name: str
    
    # Conversation
    messages: List[Dict[str, str]]
    phase: Literal["greeting", "discovery", "proposal", "closing", "done"]
    
    # Client understanding
    client_needs: Dict[str, any]  # what we learned
    missing_info: List[str]  # what we still need
    
    # Business
    proposals_made: List[Dict]  # proposals we sent
    current_offer: Optional[Dict]  # active offer
    discounts_offered: float  # total discount given
    
    # Strategy
    approach: Literal["soft", "standard", "urgent"]  # sales approach
    attempts: int  # closing attempts


def create_initial_wandero_state(company_data: Dict) -> WanderoState:
    """Initialize Wandero agent state"""
    agent_names = ["Maria", "Carlos", "Sofia", "Diego"]
    
    return WanderoState(
        company_name=company_data["name"],
        company_data=company_data,
        agent_name=random.choice(agent_names),
        messages=[],
        phase="greeting",
        client_needs={},
        missing_info=["dates", "budget", "group_size", "interests"],
        proposals_made=[],
        current_offer=None,
        discounts_offered=0.0,
        approach="standard",
        attempts=0
    )


# Node functions
def greet_and_qualify(state: WanderoState) -> Dict:
    """Warm welcome, explain company strengths"""
    company = state["company_data"]
    agent_name = state["agent_name"]
    
    # Craft greeting based on company type
    if company.get("type") == "luxury":
        greeting = f"Good day! I'm {agent_name} from {state['company_name']}. We specialize in creating exclusive, luxury travel experiences in Chile. How wonderful that you're interested in visiting! What inspired you to choose Chile as your destination?"
    elif company.get("type") == "adventure":
        greeting = f"Hey there! I'm {agent_name} from {state['company_name']}! Chile is an adventure paradise and we're experts at creating unforgettable experiences. What kind of adventures are you hoping to have?"
    elif company.get("type") == "family":
        greeting = f"Hello! I'm {agent_name} from {state['company_name']}. We're Chile's leading family travel specialists, and I'm excited to help plan your perfect family vacation. Tell me about your travel plans!"
    else:
        greeting = f"Welcome to {state['company_name']}! I'm {agent_name}, and I'd be delighted to help you plan your Chilean adventure. What brings you to Chile?"
    
    state["messages"].append({"role": "wandero", "content": greeting})
    state["phase"] = "discovery"
    
    return {"message": greeting, "state_updates": state}


def gather_details(state: WanderoState) -> Dict:
    """Ask for missing information politely"""
    missing = state["missing_info"].copy()
    questions = []
    
    # Prioritize what to ask based on what's missing
    if "dates" in missing and "dates" in state["missing_info"]:
        questions.append("When are you planning to travel?")
        state["missing_info"].remove("dates")
    
    if "group_size" in missing and len(questions) < 2:
        questions.append("How many people will be traveling?")
        if "group_size" in state["missing_info"]:
            state["missing_info"].remove("group_size")
    
    if "budget" in missing and len(questions) < 2:
        if state["company_data"].get("type") == "luxury":
            questions.append("What level of accommodation and services are you looking for?")
        else:
            questions.append("Do you have a budget range in mind?")
        if "budget" in state["missing_info"]:
            state["missing_info"].remove("budget")
    
    if "interests" in missing and len(questions) < 2:
        questions.append("What activities or experiences are most important to you?")
        if "interests" in state["missing_info"]:
            state["missing_info"].remove("interests")
    
    # Combine questions naturally
    if questions:
        message = " ".join(questions)
    else:
        message = "Is there anything specific you'd like to know about our Chile packages?"
    
    state["messages"].append({"role": "wandero", "content": message})
    
    return {"message": message, "state_updates": state}


def present_proposal(state: WanderoState) -> Dict:
    """Create detailed trip proposal with pricing"""
    company = state["company_data"]
    
    # Build proposal based on company type and known client needs
    if company.get("type") == "luxury":
        base_price = 5000
        proposal = {
            "name": "Exclusive Chile Experience",
            "duration": "10 days/9 nights",
            "highlights": [
                "5-star accommodations throughout",
                "Private guided tours",
                "Helicopter tour of Patagonia",
                "Wine tasting in exclusive vineyards",
                "Personal concierge service"
            ],
            "price_per_person": base_price
        }
    elif company.get("type") == "adventure":
        base_price = 2500
        proposal = {
            "name": "Chile Adventure Package",
            "duration": "8 days/7 nights",
            "highlights": [
                "Trekking in Torres del Paine",
                "White water rafting",
                "Volcano climbing expedition",
                "Camping under the stars",
                "Professional adventure guides"
            ],
            "price_per_person": base_price
        }
    elif company.get("type") == "family":
        base_price = 3000
        proposal = {
            "name": "Family Fun in Chile",
            "duration": "7 days/6 nights",
            "highlights": [
                "Family-friendly accommodations",
                "Penguin watching tours",
                "Interactive cooking classes",
                "Kids club activities",
                "Flexible meal times"
            ],
            "price_per_person": base_price
        }
    else:
        base_price = 2000
        proposal = {
            "name": "Classic Chile Tour",
            "duration": "7 days/6 nights",
            "highlights": [
                "Santiago city tour",
                "Valparaiso day trip",
                "Wine valley visit",
                "Comfortable 3-4 star hotels",
                "Daily breakfast included"
            ],
            "price_per_person": base_price
        }
    
    # Craft the message
    message = f"""I have the perfect package for you! Let me present our {proposal['name']}:

Duration: {proposal['duration']}

This incredible journey includes:
{chr(10).join(f'• {highlight}' for highlight in proposal['highlights'])}

Price: ${proposal['price_per_person']} per person

This package has been carefully designed to give you the authentic Chilean experience while ensuring comfort and safety throughout your journey. What do you think?"""

    state["proposals_made"].append(proposal)
    state["current_offer"] = proposal
    state["phase"] = "proposal"
    state["messages"].append({"role": "wandero", "content": message})
    
    return {"message": message, "state_updates": state}


def handle_objection(state: WanderoState) -> Dict:
    """Address specific concerns raised"""
    # Look at recent messages to understand the concern
    recent_client_message = ""
    for msg in reversed(state["messages"]):
        if msg["role"] == "client":
            recent_client_message = msg["content"].lower()
            break
    
    # Address common concerns
    if "safety" in recent_client_message or "child" in recent_client_message:
        message = """I completely understand your concern about safety. Let me assure you:

• All our destinations are in safe, tourist-friendly areas
• We work only with certified, experienced guides
• Our accommodations are family-friendly with 24/7 security
• We provide comprehensive travel insurance
• Emergency medical facilities are always within reach
• We have special protocols for families with children

Your family's safety is our top priority. We also provide a 24/7 emergency hotline throughout your trip."""

    elif "price" in recent_client_message or "expensive" in recent_client_message or "budget" in recent_client_message:
        message = """I understand budget is an important consideration. Let me break down the value:

• All accommodations and transfers included
• Most meals covered (saving you $50-100/day)
• Expert guides who enhance your experience
• Skip-the-line access at attractions
• No hidden fees - everything is transparent

When you consider everything included, it's actually excellent value. Plus, we offer flexible payment plans!"""

    elif "cancel" in recent_client_message or "policy" in recent_client_message:
        message = """Great question about our cancellation policy! We offer:

• Full refund up to 30 days before travel
• 75% refund 15-29 days before
• 50% refund 7-14 days before
• Travel insurance option for additional protection
• Free rescheduling up to 14 days before travel

We understand plans can change, so we've made our policy as flexible as possible."""

    else:
        message = """I appreciate you sharing your concerns. Let me address that:

We've been operating in Chile for over 10 years and have helped thousands of travelers have amazing experiences. Our team is dedicated to ensuring every aspect of your trip exceeds expectations.

Is there a specific aspect you'd like me to clarify further?"""
    
    state["messages"].append({"role": "wandero", "content": message})
    
    return {"message": message, "state_updates": state}


def offer_incentive(state: WanderoState) -> Dict:
    """Provide discount (max from company data)"""
    company = state["company_data"]
    max_discount = company.get("max_discount", 0.1)  # Default 10% if not specified
    
    # Calculate discount based on attempts
    if state["discounts_offered"] >= max_discount:
        message = "I've already given you our best possible price. This really is an exceptional value for what's included."
    else:
        # Offer incremental discount
        if state["attempts"] == 0:
            discount = 0.05  # 5% first attempt
        else:
            discount = 0.1  # 10% second attempt
        
        discount = min(discount, max_discount - state["discounts_offered"])
        state["discounts_offered"] += discount
        
        if state["current_offer"]:
            original_price = state["current_offer"]["price_per_person"]
            discounted_price = int(original_price * (1 - state["discounts_offered"]))
            savings = int(original_price * state["discounts_offered"])
            
            message = f"""I can see you're seriously interested, so let me make this easier for you. 

If you book today, I can offer you a special discount of {int(discount * 100)}% off! 

That brings your price down to ${discounted_price} per person (saving ${savings} per person).

This is a limited-time offer that I can only hold for the next 24 hours. What do you say?"""
        else:
            message = "Let me see what special offers I can apply to make this work better for your budget."
    
    state["attempts"] += 1
    state["approach"] = "urgent" if state["attempts"] > 1 else "soft"
    state["messages"].append({"role": "wandero", "content": message})
    
    return {"message": message, "state_updates": state}


def close_deal(state: WanderoState) -> Dict:
    """Finalize booking, send confirmation"""
    agent_name = state["agent_name"]
    
    message = f"""Fantastic! I'm so excited for your upcoming adventure in Chile!

Let me confirm your booking:
{state['current_offer']['name']} - {state['current_offer']['duration']}

Next steps:
1. I'll send you a booking confirmation email within the next hour
2. You'll receive a detailed itinerary within 24 hours
3. Our travel concierge will contact you 1 week before departure
4. Your welcome packet will arrive 2 weeks before travel

Is the email address we have on file the best one to use?

Thank you for choosing {state['company_name']}! If you have any questions before your trip, please don't hesitate to reach out to me directly.

¡Nos vemos en Chile!
- {agent_name}"""

    state["phase"] = "done"
    state["messages"].append({"role": "wandero", "content": message})
    
    return {"message": message, "state_updates": state}


def follow_up(state: WanderoState) -> Dict:
    """Schedule future contact if undecided"""
    agent_name = state["agent_name"]
    
    messages = [
        f"""I completely understand you need time to think this through. This is an important decision!

I'll send you an email with all the details we discussed today, including the special pricing I offered.

Would it be okay if I follow up with you in a couple of days to answer any questions that might come up? 

In the meantime, feel free to reach out anytime - I'm here to help make your Chile dream a reality!

Best regards,
{agent_name}""",

        f"""Of course! Take all the time you need. Travel planning should be exciting, not stressful.

I'll email you a summary of our conversation along with some additional Chile travel inspiration.

When would be a good time for me to check back with you? I want to make sure you have all the information you need.

Looking forward to hopefully helping you explore Chile!
- {agent_name}"""
    ]
    
    message = random.choice(messages)
    state["messages"].append({"role": "wandero", "content": message})
    
    return {"message": message, "state_updates": state}


def accept_loss(state: WanderoState) -> Dict:
    """Politely end if client not interested"""
    agent_name = state["agent_name"]
    
    message = f"""I understand, and I appreciate you taking the time to explore options with us.

If your plans change or if you'd like to explore Chile in the future, please don't hesitate to reach out. We'd be happy to help whenever you're ready.

Wishing you wonderful travels wherever your journey takes you!

Best regards,
{agent_name}
{state['company_name']}"""

    state["phase"] = "done"
    state["messages"].append({"role": "wandero", "content": message})
    
    return {"message": message, "state_updates": state}


def get_wandero_action(state: WanderoState, llm) -> str:
    """Use LLM to decide next Wandero action based on state"""
    
    # Build context
    last_message = ""
    for msg in reversed(state["messages"]):
        if msg["role"] == "client":
            last_message = msg["content"]
            break
    
    prompt = f"""You are orchestrating a travel agent's behavior in a sales conversation.

Agent: {state['agent_name']} from {state['company_name']}
Company type: {state['company_data'].get('type', 'standard')}
Current phase: {state['phase']}
Messages exchanged: {len(state['messages'])}
Discounts given: {state['discounts_offered']}
Attempts made: {state['attempts']}

Last message from client:
{last_message}

Current state:
- Missing info: {state['missing_info']}
- Proposals made: {len(state['proposals_made'])}
- Current approach: {state['approach']}

Available actions:
1. greet_and_qualify - Welcome and understand needs (only at start)
2. gather_details - Ask for missing information
3. present_proposal - Show package with pricing
4. handle_objection - Address concerns
5. offer_incentive - Provide discount
6. close_deal - Finalize booking
7. follow_up - Schedule future contact
8. accept_loss - End politely if not interested

Based on the conversation flow and client's message, which action should the agent take?
Consider:
- Has the client shown interest or concerns?
- Do we have enough information to make a proposal?
- Is the client ready to book or needs more convincing?
- Should we push harder or accept the situation?

Return ONLY the action name."""

    response = llm.invoke(prompt)
    action = response.strip().lower().replace(" ", "_")
    
    # Validate and provide fallback
    valid_actions = ["greet_and_qualify", "gather_details", "present_proposal",
                    "handle_objection", "offer_incentive", "close_deal",
                    "follow_up", "accept_loss"]
    
    if action not in valid_actions:
        # Smart fallback based on state
        if not state["messages"]:
            return "greet_and_qualify"
        elif len(state["missing_info"]) > 2:
            return "gather_details"
        elif not state["proposals_made"]:
            return "present_proposal"
        elif "book" in last_message.lower() or "yes" in last_message.lower():
            return "close_deal"
        elif "no" in last_message.lower() or "sorry" in last_message.lower():
            return "accept_loss"
        else:
            return "handle_objection"
    
    return action


def execute_wandero_node(action: str, state: WanderoState) -> str:
    """Execute the specified Wandero action"""
    node_map = {
        "greet_and_qualify": greet_and_qualify,
        "gather_details": gather_details,
        "present_proposal": present_proposal,
        "handle_objection": handle_objection,
        "offer_incentive": offer_incentive,
        "close_deal": close_deal,
        "follow_up": follow_up,
        "accept_loss": accept_loss
    }
    
    if action in node_map:
        result = node_map[action](state)
        return result["message"]
    else:
        return "How can I help you with your travel plans?"