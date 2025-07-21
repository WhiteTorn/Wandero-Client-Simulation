from typing import TypedDict, List, Dict, Literal, Optional
import random
from datetime import datetime

class WanderoState(TypedDict):
    """Enhanced Wandero state for LLM-driven conversations"""
    # Identity  
    company_name: str
    company_data: Dict
    agent_name: str
    
    # Conversation
    messages: List[Dict[str, str]]  # role, content, subject
    phase: Literal["introduction", "discovery", "proposal", "negotiation", "closing", "done"]
    
    # Client understanding
    client_needs: Dict[str, any]
    missing_info: List[str]
    client_concerns: List[str]
    
    # Business
    proposals_made: List[Dict]
    current_offer: Optional[Dict]
    discounts_offered: float
    
    # Strategy
    approach: Literal["soft", "standard", "urgent"]
    attempts: int
    last_email_subject: str


def create_initial_wandero_state(company_data: Dict) -> WanderoState:
    """Initialize Wandero agent state"""
    agent_names = ["Maria Rodriguez", "Carlos Mendez", "Sofia Vargas", "Diego Silva"]
    
    return WanderoState(
        company_name=company_data["name"],
        company_data=company_data,
        agent_name=random.choice(agent_names),
        messages=[],
        phase="introduction",
        client_needs={},
        missing_info=["dates", "budget", "group_size", "interests", "special_requirements"],
        client_concerns=[],
        proposals_made=[],
        current_offer=None,
        discounts_offered=0.0,
        approach="standard",
        attempts=0,
        last_email_subject=f"Welcome to {company_data['name']} - Your Chilean Adventure Awaits!"
    )


def generate_wandero_email(state: WanderoState, action: str, llm) -> Dict:
    """Generate email content using LLM based on action and state"""
    
    # Build comprehensive context
    context = f"""You are {state['agent_name']}, a travel agent at {state['company_name']}.

Company profile:
- Type: {state['company_data'].get('type')}
- Specialties: {', '.join(state['company_data'].get('specialties', []))}
- Price range: ${state['company_data'].get('price_range', {}).get('min', 0)}-${state['company_data'].get('price_range', {}).get('max', 0)} per day
- Unique points: {chr(10).join('• ' + point for point in state['company_data'].get('unique_selling_points', []))}
- Target audience: {state['company_data'].get('target_audience')}

Current situation:
- Phase: {state['phase']}
- Messages exchanged: {len(state['messages'])}
- Missing info: {', '.join(state['missing_info']) if state['missing_info'] else 'have all needed info'}
- Client concerns noted: {', '.join(state['client_concerns']) if state['client_concerns'] else 'none noted'}
- Discounts offered: {state['discounts_offered']*100:.0f}%
- Sales approach: {state['approach']}

What you know about the client:
{chr(10).join(f"- {k}: {v}" for k, v in state['client_needs'].items()) if state['client_needs'] else "- No information yet"}
"""

    # Action-specific prompts
    if action == "greet_and_qualify":
        prompt = context + f"""
Write the FIRST email to a potential client who just inquired. This is your introduction email.

Guidelines:
- Introduce yourself and {state['company_name']}
- Highlight what makes your company special (based on company type)
- Show enthusiasm about Chile
- Ask 1-2 open-ended questions to understand their needs
- Keep it warm but professional
- If luxury company: emphasize exclusivity
- If adventure company: emphasize excitement
- If family company: emphasize safety and fun

Format as:
Subject: {state['last_email_subject']}
[Email body with professional signature including your name and title]"""

    elif action == "gather_details":
        recent_msg = state['messages'][-1]['content'] if state['messages'] else ""
        prompt = context + f"""
Client's last email:
"{recent_msg}"

You need more information to create a great proposal. Ask about missing details naturally.
Don't ask more than 2-3 questions at once.
Priority: dates, group size, interests, budget (but be tactful about budget).

Format as:
Subject: Re: {state.get('last_email_subject', 'Your Chile Travel Inquiry')}
[Email body]"""

    elif action == "present_proposal":
        prompt = context + f"""
Create a detailed, enticing proposal based on what you know about the client.

Guidelines:
- Match proposal to company type and client needs
- Include specific itinerary highlights
- Mention accommodations level
- State the price clearly
- Add value propositions
- Create excitement about the experience
- For families: emphasize safety and kid-friendly aspects
- For adventure: emphasize unique experiences
- For luxury: emphasize exclusivity and comfort

Make it visual and appealing with good formatting.

Format as:
Subject: Your Personalized Chile Adventure Proposal
[Email body with detailed proposal]"""

    elif action == "handle_objection":
        recent_msg = state['messages'][-1]['content'] if state['messages'] else ""
        concerns = state['client_concerns'] if state['client_concerns'] else ["general concern"]
        
        prompt = context + f"""
Client's message expressing concern:
"{recent_msg}"

Address their specific concern professionally and thoroughly.
- If about safety: Provide concrete safety measures
- If about price: Explain value and what's included
- If about logistics: Give detailed information
- Use your company's strengths to reassure them

Be empathetic and detailed without being pushy.

Format as:
Subject: Re: {state.get('last_email_subject', 'Your Chile Travel Inquiry')}
[Email body]"""

    elif action == "offer_incentive":
        max_discount = state['company_data'].get('max_discount', 0.15)
        remaining_discount = max_discount - state['discounts_offered']
        
        prompt = context + f"""
The client is interested but hesitating (probably about price).
You can offer up to {remaining_discount*100:.0f}% additional discount.

Create an email with a special offer:
- Make it time-sensitive
- Explain this is a special rate
- Add extra value if possible (upgrades, extras)
- Show enthusiasm about having them as clients
- Create gentle urgency without being pushy

Current pricing should reflect total discount of {(state['discounts_offered'] + min(0.05, remaining_discount))*100:.0f}%.

Format as:
Subject: Special Offer for Your Chile Adventure
[Email body]"""

    elif action == "close_deal":
        prompt = context + """
The client has agreed to book! Write a confirmation email that:
- Shows genuine excitement
- Confirms key details
- Outlines clear next steps
- Provides your direct contact
- Makes them feel they made a great choice
- Includes payment instructions
- Sets expectations for documents/information needed

Make it warm and professional.

Format as:
Subject: Welcome Aboard! Your Chile Adventure is Confirmed
[Email body with full signature and contact details]"""

    elif action == "follow_up":
        prompt = context + """
The client needs time to think. Write a thoughtful follow-up that:
- Respects their need for time
- Offers to send additional information
- Mentions you'll hold the quoted rate for a few days
- Provides your direct contact
- Suggests a follow-up timeline
- Stays helpful without being pushy

Format as:
Subject: Re: {state.get('last_email_subject', 'Your Chile Travel Proposal')}
[Email body]"""

    elif action == "accept_loss":
        prompt = context + """
The client has decided not to book. Write a gracious closing email that:
- Thanks them for their time
- Leaves the door open for future travel
- Wishes them well
- Provides your contact for future needs
- Stays professional and friendly

Keep it brief and classy.

Format as:
Subject: Re: {state.get('last_email_subject', 'Your Chile Travel Inquiry')}
[Email body]"""

    # Generate email
    response = llm.generate_content(prompt)
    
    # Parse response
    lines = response.text.strip().split('\n')
    subject = ""
    body_lines = []
    
    for i, line in enumerate(lines):
        if line.startswith("Subject:"):
            subject = line.replace("Subject:", "").strip()
        elif i > 0:
            body_lines.append(line)
    
    body = '\n'.join(body_lines).strip()
    
    # Update state based on action and content
    if action == "greet_and_qualify":
        state["phase"] = "discovery"
    
    elif action == "gather_details":
        # Track what we're asking about
        for info in state["missing_info"][:]:
            if info in body.lower():
                # We asked about it, might get answer next
                pass
    
    elif action == "present_proposal":
        # Create a basic proposal structure
        if state["company_data"].get("type") == "luxury":
            base_price = 800
        elif state["company_data"].get("type") == "adventure":
            base_price = 350
        elif state["company_data"].get("type") == "family":
            base_price = 450
        else:
            base_price = 300
            
        proposal = {
            "base_price_per_day": base_price,
            "presented_at": datetime.now().isoformat(),
            "includes": "accommodations, transfers, guided tours, some meals"
        }
        state["proposals_made"].append(proposal)
        state["current_offer"] = proposal
        state["phase"] = "proposal"
    
    elif action == "handle_objection":
        # Note that we addressed concerns
        state["attempts"] += 1
    
    elif action == "offer_incentive":
        # Apply discount
        max_discount = state["company_data"].get('max_discount', 0.15)
        if state["discounts_offered"] < max_discount:
            state["discounts_offered"] = min(state["discounts_offered"] + 0.05, max_discount)
        state["approach"] = "urgent"
        state["phase"] = "negotiation"
    
    elif action == "close_deal":
        state["phase"] = "done"
    
    elif action == "follow_up":
        state["phase"] = "done"
    
    elif action == "accept_loss":
        state["phase"] = "done"
    
    # Store the email
    state["messages"].append({
        "role": "wandero",
        "content": body,
        "subject": subject
    })
    state["last_email_subject"] = subject
    
    return {"subject": subject, "body": body, "state": state}


def get_wandero_action(state: WanderoState, llm) -> str:
    """Use LLM to intelligently decide next action"""
    
    # Build conversation context
    conversation_summary = "Starting new conversation"
    if state["messages"]:
        recent_msgs = state["messages"][-3:]
        conversation_summary = "\n".join([
            f"{msg['role']}: {msg['content'][:100]}..." for msg in recent_msgs
        ])
    
    # Analyze client's last message for concerns
    client_sentiment = "neutral"
    if state["messages"]:
        for msg in reversed(state["messages"]):
            if msg["role"] == "client":
                last_client_msg = msg["content"].lower()
                if any(word in last_client_msg for word in ["worried", "concern", "afraid", "safety", "expensive"]):
                    client_sentiment = "concerned"
                elif any(word in last_client_msg for word in ["excited", "love", "perfect", "great", "yes"]):
                    client_sentiment = "positive"
                elif any(word in last_client_msg for word in ["no", "sorry", "cannot", "won't"]):
                    client_sentiment = "negative"
                break
    
    prompt = f"""You are orchestrating a travel agent's sales strategy.

Company: {state['company_name']} ({state['company_data'].get('type')} travel)
Current phase: {state['phase']}
Messages exchanged: {len(state['messages'])}
Client sentiment: {client_sentiment}

Recent conversation:
{conversation_summary}

Current status:
- Missing information: {len(state['missing_info'])} items
- Proposals made: {len(state['proposals_made'])}
- Discounts offered: {state['discounts_offered']*100:.0f}%
- Maximum allowed discount: {state['company_data'].get('max_discount', 0.15)*100:.0f}%

Available actions:
1. greet_and_qualify - Initial introduction (only if no messages yet)
2. gather_details - Ask for missing information
3. present_proposal - Show detailed package/pricing
4. handle_objection - Address specific concerns
5. offer_incentive - Provide discount/special offer
6. close_deal - Finalize booking (if client agrees)
7. follow_up - Schedule future contact
8. accept_loss - End gracefully if not interested

Analyze the conversation and choose the most appropriate sales action.
Consider:
- Do we have enough info to make a proposal?
- Has the client expressed specific concerns to address?
- Are they ready to book or need more convincing?
- Have we been too pushy? Should we back off?

Return ONLY the action name."""

    response = llm.generate_content(prompt)
    action = response.text.strip().lower().replace(" ", "_")
    
    # Validate action
    valid_actions = ["greet_and_qualify", "gather_details", "present_proposal",
                    "handle_objection", "offer_incentive", "close_deal",
                    "follow_up", "accept_loss"]
    
    if action not in valid_actions:
        # Smart fallback based on conversation state
        if not state["messages"]:
            return "greet_and_qualify"
        elif client_sentiment == "concerned":
            return "handle_objection"
        elif client_sentiment == "positive" and state["proposals_made"]:
            return "close_deal"
        elif client_sentiment == "negative":
            return "accept_loss"
        elif len(state["missing_info"]) > 2 and not state["proposals_made"]:
            return "gather_details"
        elif not state["proposals_made"] and len(state["messages"]) > 2:
            return "present_proposal"
        else:
            return "follow_up"
    
    return action


def parse_client_info(state: WanderoState, client_message: str):
    """Extract client information from their message"""
    message_lower = client_message.lower()
    
    # Extract dates
    if any(month in message_lower for month in ["january", "february", "march", "april", "may", "june", 
                                                 "july", "august", "september", "october", "november", "december"]):
        if "dates" in state["missing_info"]:
            state["missing_info"].remove("dates")
        state["client_needs"]["travel_dates"] = "mentioned in email"
    
    # Extract budget
    if "$" in client_message or "budget" in message_lower:
        if "budget" in state["missing_info"]:
            state["missing_info"].remove("budget")
        state["client_needs"]["budget"] = "mentioned in email"
    
    # Extract group size
    if any(word in message_lower for word in ["solo", "alone", "myself", "couple", "two", "family", 
                                               "children", "kids", "group"]):
        if "group_size" in state["missing_info"]:
            state["missing_info"].remove("group_size")
        state["client_needs"]["group_size"] = "mentioned in email"
    
    # Extract interests
    if any(word in message_lower for word in ["adventure", "hiking", "wine", "culture", "relax", 
                                               "beach", "mountain", "city"]):
        if "interests" in state["missing_info"]:
            state["missing_info"].remove("interests")
        state["client_needs"]["interests"] = "mentioned in email"
    
    # Extract concerns
    concern_keywords = {
        "safety": ["safe", "security", "dangerous", "crime"],
        "health": ["medical", "hospital", "doctor", "allergy", "dietary"],
        "cost": ["expensive", "afford", "cheaper", "budget", "cost"],
        "weather": ["weather", "rain", "cold", "hot", "season"]
    }
    
    for concern_type, keywords in concern_keywords.items():
        if any(keyword in message_lower for keyword in keywords):
            if concern_type not in state["client_concerns"]:
                state["client_concerns"].append(concern_type)