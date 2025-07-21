from typing import TypedDict, List, Dict, Literal, Optional
import random
from datetime import datetime, timedelta

class ClientState(TypedDict):
    """Simple but complete client state"""
    # Identity
    persona_name: str 
    persona_data: Dict  # Full persona dict from personas.py
    
    # Conversation
    messages: List[Dict[str, str]]  # role, content
    phase: Literal["exploring", "interested", "deciding", "booking", "done"]
    
    # What we know/shared
    shared_info: Dict[str, bool]  # what info we've shared
    concerns: List[str]  # current concerns
    likes: List[str]  # what they liked
    
    # Decision tracking
    interest_level: float  # 0-1
    ready_to_book: bool
    abandonment_risk: float  # 0-1
    
    # Simple memory
    important_points: List[str]  # things to remember
    forgot_to_mention: List[str]  # for realistic behavior


def create_initial_client_state(persona_data: Dict) -> ClientState:
    """Initialize client state from persona data"""
    # Extract things they might forget to mention initially
    forgot_items = []
    if "special_requirements" in persona_data:
        forgot_items.extend(persona_data["special_requirements"][:1])  # Forget one requirement
    
    return ClientState(
        persona_name=persona_data["name"],
        persona_data=persona_data,
        messages=[],
        phase="exploring",
        shared_info={
            "dates_shared": False,
            "budget_shared": False,
            "destination_shared": False,
            "group_size_shared": False,
            "preferences_shared": False
        },
        concerns=persona_data.get("worries", []).copy(),
        likes=[],
        interest_level=0.3,  # Start neutral
        ready_to_book=False,
        abandonment_risk=0.1,
        important_points=[],
        forgot_to_mention=forgot_items
    )


# Node functions
def initial_inquiry(state: ClientState) -> Dict:
    """First contact with agency"""
    persona = state["persona_data"]
    destination = persona.get("preferred_destinations", ["Chile"])[0]
    
    # Craft initial message based on personality
    if persona.get("personality") == "spontaneous":
        message = f"Hi! I just heard about {destination} and I'm super excited to plan a trip! Can you help me?"
    elif persona.get("personality") == "cautious":
        message = f"Hello, I'm considering a trip to {destination} and would like to learn more about your services."
    else:
        message = f"Hi there! I'm interested in planning a trip to {destination}. What options do you have?"
    
    # Update state
    state["shared_info"]["destination_shared"] = True
    state["phase"] = "exploring"
    state["messages"].append({"role": "client", "content": message})
    
    return {"message": message, "state_updates": state}


def provide_details(state: ClientState) -> Dict:
    """Share trip information based on what's asked"""
    persona = state["persona_data"]
    details_to_share = []
    
    # Check what hasn't been shared yet
    if not state["shared_info"]["dates_shared"]:
        travel_dates = persona.get("travel_dates", "next month")
        details_to_share.append(f"I'm looking to travel {travel_dates}")
        state["shared_info"]["dates_shared"] = True
    
    if not state["shared_info"]["budget_shared"] and random.random() > 0.5:
        budget = persona.get("budget", "flexible")
        if isinstance(budget, dict):
            details_to_share.append(f"My budget is around ${budget.get('max', 'flexible')}")
        else:
            details_to_share.append(f"Budget-wise, I'm {budget}")
        state["shared_info"]["budget_shared"] = True
    
    if not state["shared_info"]["group_size_shared"]:
        group = persona.get("travel_group", "solo")
        details_to_share.append(f"I'll be traveling {group}")
        state["shared_info"]["group_size_shared"] = True
    
    if not state["shared_info"]["preferences_shared"] and len(details_to_share) < 2:
        prefs = persona.get("interests", [])
        if prefs:
            details_to_share.append(f"I'm particularly interested in {', '.join(prefs[:2])}")
        state["shared_info"]["preferences_shared"] = True
    
    message = ". ".join(details_to_share) if details_to_share else "I think I've shared most of the details already."
    state["messages"].append({"role": "client", "content": message})
    
    return {"message": message, "state_updates": state}


def express_interest(state: ClientState) -> Dict:
    """React positively to proposals"""
    persona = state["persona_data"]
    
    # Different ways to express interest based on personality
    if persona.get("personality") == "spontaneous":
        responses = [
            "Oh wow, that sounds amazing! Tell me more!",
            "I love it! This is exactly what I was hoping for!",
            "That's perfect! When can we make this happen?"
        ]
    elif persona.get("personality") == "cautious":
        responses = [
            "This sounds quite good. I'd like to know more details.",
            "I'm interested. Could you elaborate on the safety measures?",
            "That seems reasonable. What are the next steps?"
        ]
    else:
        responses = [
            "That sounds great! I'm definitely interested.",
            "This looks like a good option. What else is included?",
            "I like what I'm hearing. Let's explore this further."
        ]
    
    message = random.choice(responses)
    
    # Update state
    state["interest_level"] = min(state["interest_level"] + 0.2, 0.9)
    state["phase"] = "interested"
    state["messages"].append({"role": "client", "content": message})
    
    # Add what they liked
    if len(state["messages"]) > 2:
        state["likes"].append("Recent proposal details")
    
    return {"message": message, "state_updates": state}


def raise_concern(state: ClientState) -> Dict:
    """Ask about worries from persona data"""
    concerns = state["concerns"]
    
    if not concerns:
        # Generic concerns based on persona type
        persona = state["persona_data"]
        if "parent" in persona.get("name", "").lower():
            concerns = ["child safety", "medical facilities", "family-friendly activities"]
        elif "budget" in persona.get("name", "").lower():
            concerns = ["hidden costs", "value for money", "cheaper alternatives"]
        else:
            concerns = ["cancellation policy", "weather conditions", "accommodation quality"]
    
    # Pick a concern to raise
    if concerns:
        concern = concerns.pop(0)
        
        if concern == "child safety":
            message = "I'm a bit worried about safety, especially since I'll be traveling with children. What measures are in place?"
        elif concern == "medical facilities":
            message = "What about medical facilities? Are there hospitals nearby in case of emergencies?"
        elif concern == "hidden costs":
            message = "Are there any additional fees I should know about? I want to make sure I stay within budget."
        elif concern == "cancellation policy":
            message = "What's your cancellation policy? Just in case our plans change."
        else:
            message = f"I have a question about {concern}. Can you provide more information?"
        
        state["abandonment_risk"] = max(state["abandonment_risk"] - 0.1, 0)  # Asking questions reduces abandonment
    else:
        message = "I think most of my concerns have been addressed. Thank you!"
    
    state["messages"].append({"role": "client", "content": message})
    
    return {"message": message, "state_updates": state}


def negotiate(state: ClientState) -> Dict:
    """Try to get better pricing or terms"""
    persona = state["persona_data"]
    
    if persona.get("personality") == "budget-conscious" or "budget" in persona.get("name", "").lower():
        negotiations = [
            "Is there any flexibility on the price? Maybe if we book for a longer duration?",
            "Do you have any current promotions or discounts available?",
            "What if we skip some of the premium add-ons? How much would that save?"
        ]
    else:
        negotiations = [
            "Is there any way to get a better deal on this package?",
            "What about group discounts? We might have friends interested too.",
            "Can we customize this package to better fit our needs and budget?"
        ]
    
    message = random.choice(negotiations)
    
    state["phase"] = "deciding"
    state["messages"].append({"role": "client", "content": message})
    
    return {"message": message, "state_updates": state}


def make_decision(state: ClientState) -> Dict:
    """Accept or decline based on interest level"""
    
    if state["interest_level"] > 0.7 and state["abandonment_risk"] < 0.5:
        # Accept
        persona = state["persona_data"]
        if persona.get("personality") == "spontaneous":
            message = "Yes! Let's do this! I'm ready to book right now!"
        elif persona.get("personality") == "cautious":
            message = "After careful consideration, I'd like to proceed with the booking. What are the next steps?"
        else:
            message = "Great, I'm ready to book. Please send me the confirmation details."
        
        state["ready_to_book"] = True
        state["phase"] = "booking"
    else:
        # Polite decline
        if state["interest_level"] < 0.4:
            message = "Thank you for all the information, but I don't think this is quite right for me at this time."
        else:
            message = "I appreciate your help. Let me think about it and get back to you. Can I have your contact information?"
        
        state["phase"] = "done"
    
    state["messages"].append({"role": "client", "content": message})
    
    return {"message": message, "state_updates": state}


def send_correction(state: ClientState) -> Dict:
    """Remember and share forgotten details"""
    if state["forgot_to_mention"]:
        forgotten_detail = state["forgot_to_mention"].pop(0)
        
        messages = [
            f"Oh, I just remembered - {forgotten_detail}. Is that going to be a problem?",
            f"Sorry, I forgot to mention earlier: {forgotten_detail}. Hope that's okay!",
            f"One more thing I should have said: {forgotten_detail}. Does that change anything?"
        ]
        
        message = random.choice(messages)
        state["important_points"].append(forgotten_detail)
    else:
        message = "I think I've covered everything now. Thanks for your patience!"
    
    state["messages"].append({"role": "client", "content": message})
    
    return {"message": message, "state_updates": state}


def abandon(state: ClientState) -> Dict:
    """Leave if abandonment risk is high"""
    persona = state["persona_data"]
    
    if persona.get("personality") == "cautious":
        message = "I need to think about this more. Thank you for your time."
    elif persona.get("personality") == "spontaneous":
        message = "Actually, I just realized this might not be the right time. Sorry!"
    else:
        message = "I don't think this is going to work out. Thanks anyway."
    
    state["phase"] = "done"
    state["messages"].append({"role": "client", "content": message})
    
    return {"message": message, "state_updates": state}


def get_client_action(state: ClientState, llm) -> str:
    """Use LLM to decide next client action based on state"""
    
    # Build context for LLM
    last_message = state["messages"][-1]["content"] if state["messages"] else "None yet"
    
    prompt = f"""You are orchestrating a client's behavior in a travel booking conversation.

Client: {state['persona_name']}
Personality: {state['persona_data'].get('personality', 'standard')}
Current phase: {state['phase']}
Interest level: {state['interest_level']}
Abandonment risk: {state['abandonment_risk']}
Messages exchanged: {len(state['messages'])}

Last message from Wandero:
{last_message}

Client's current state:
- Shared info: {state['shared_info']}
- Concerns remaining: {len(state['concerns'])}
- Things liked: {len(state['likes'])}
- Forgot to mention: {len(state['forgot_to_mention'])}

Available actions:
1. initial_inquiry - Make first contact (only if no messages yet)
2. provide_details - Share trip information
3. express_interest - Show interest in proposal
4. raise_concern - Ask about worries
5. negotiate - Try for better deal
6. make_decision - Accept or decline
7. send_correction - Remember forgotten detail
8. abandon - Leave conversation

Based on the personality and conversation flow, which action should the client take next?
Consider:
- Is this personality type cautious or spontaneous?
- Have they shared enough information?
- Are they happy with the proposal?
- Would they realistically continue or leave?

Return ONLY the action name."""

    response = llm.invoke(prompt)
    action = response.strip().lower().replace(" ", "_")
    
    # Validate action
    valid_actions = ["initial_inquiry", "provide_details", "express_interest", 
                    "raise_concern", "negotiate", "make_decision", 
                    "send_correction", "abandon"]
    
    if action not in valid_actions:
        # Default fallback based on state
        if not state["messages"]:
            return "initial_inquiry"
        elif state["phase"] == "exploring":
            return "provide_details"
        elif state["interest_level"] > 0.7:
            return "make_decision"
        else:
            return "raise_concern"
    
    return action


# Node execution
def execute_client_node(action: str, state: ClientState) -> str:
    """Execute the specified client action"""
    node_map = {
        "initial_inquiry": initial_inquiry,
        "provide_details": provide_details,
        "express_interest": express_interest,
        "raise_concern": raise_concern,
        "negotiate": negotiate,
        "make_decision": make_decision,
        "send_correction": send_correction,
        "abandon": abandon
    }
    
    if action in node_map:
        result = node_map[action](state)
        return result["message"]
    else:
        return "I'm not sure what to say."