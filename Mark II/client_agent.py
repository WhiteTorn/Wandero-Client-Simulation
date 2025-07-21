from typing import TypedDict, List, Dict, Literal, Optional
import random
from datetime import datetime

class ClientState(TypedDict):
    """Enhanced client state for LLM-driven conversations"""
    # Identity
    persona_name: str
    persona_data: Dict
    
    # Conversation
    messages: List[Dict[str, str]]  # role, content, subject
    phase: Literal["initial", "exploring", "interested", "deciding", "booking", "done"]
    
    # What we know/shared
    shared_info: Dict[str, bool]
    concerns: List[str]
    likes: List[str]
    
    # Decision tracking
    interest_level: float
    ready_to_book: bool
    abandonment_risk: float
    
    # Memory
    important_points: List[str]
    forgot_to_mention: List[str]
    last_email_subject: str


def create_initial_client_state(persona_data: Dict) -> ClientState:
    """Initialize client state from persona data"""
    forgot_items = []
    if "special_requirements" in persona_data:
        # Realistically forget some requirements
        if random.random() > 0.6:
            forgot_items.append(random.choice(persona_data["special_requirements"]))
    
    return ClientState(
        persona_name=persona_data["name"],
        persona_data=persona_data,
        messages=[],
        phase="initial",
        shared_info={
            "dates_shared": False,
            "budget_shared": False,
            "destination_shared": False,
            "group_size_shared": False,
            "preferences_shared": False,
            "special_requirements_shared": False
        },
        concerns=persona_data.get("worries", []).copy(),
        likes=[],
        interest_level=0.3,
        ready_to_book=False,
        abandonment_risk=0.1,
        important_points=[],
        forgot_to_mention=forgot_items,
        last_email_subject=""
    )


def generate_client_email(state: ClientState, action: str, llm) -> Dict:
    """Generate email content using LLM based on action and state"""
    
    # Build comprehensive context for LLM
    context = f"""You are {state['persona_name']}, writing an email to a travel agency.

Your personality: {state['persona_data'].get('personality')}
Your background:
- Travel group: {state['persona_data'].get('travel_group')}
- Interests: {', '.join(state['persona_data'].get('interests', []))}
- Budget: ${state['persona_data'].get('budget', {}).get('min', 0)}-${state['persona_data'].get('budget', {}).get('max', 0)}
- Travel dates: {state['persona_data'].get('travel_dates')}
- Decision style: {state['persona_data'].get('decision_style')}

Current situation:
- Phase: {state['phase']}
- Interest level: {state['interest_level']:.1f}/1.0
- Concerns: {', '.join(state['concerns']) if state['concerns'] else 'none currently'}
- Things you forgot to mention: {', '.join(state['forgot_to_mention']) if state['forgot_to_mention'] else 'nothing'}

What you've already shared:
{chr(10).join(f"- {k.replace('_', ' ')}: {'yes' if v else 'no'}" for k, v in state['shared_info'].items())}

Action to take: {action}
"""

    # Add action-specific instructions
    if action == "initial_inquiry":
        prompt = context + """
Write your first email to the travel agency. You just received their introduction email.
- Express interest in traveling to your preferred destination
- Be natural - don't share everything at once
- Match your personality (cautious people are more formal, spontaneous more casual)
- Ask a general question to start the conversation

Format as:
Subject: [appropriate subject line]
[Email body with proper greeting and sign-off]"""

    elif action == "provide_details":
        recent_msg = state['messages'][-1]['content'] if state['messages'] else ""
        prompt = context + f"""
The agency asked for more information. Their last email:
"{recent_msg}"

Reply with relevant details they asked for. Don't overshare - provide 2-3 pieces of information maximum.
If they asked about budget and you're budget-conscious, you might be vague at first.
Stay true to your personality.

Format as:
Subject: Re: {state.get('last_email_subject', 'Travel Inquiry')}
[Email body]"""

    elif action == "express_interest":
        recent_msg = state['messages'][-1]['content'] if state['messages'] else ""
        prompt = context + f"""
The agency presented a proposal. Their last email:
"{recent_msg}"

Show genuine interest based on your personality:
- Spontaneous: Very enthusiastic
- Cautious: Positive but measured
- Budget-conscious: Focus on value

Ask follow-up questions that matter to you.

Format as:
Subject: Re: {state.get('last_email_subject', 'Travel Proposal')}
[Email body]"""

    elif action == "raise_concern":
        concern = state['concerns'][0] if state['concerns'] else "general concerns"
        prompt = context + f"""
You need to ask about: {concern}

Write an email expressing this concern naturally. 
- Parents worry about safety
- Budget travelers worry about hidden costs
- Solo travelers worry about meeting others

Be specific and genuine.

Format as:
Subject: Re: {state.get('last_email_subject', 'Travel Inquiry')} - Quick Question
[Email body]"""

    elif action == "negotiate":
        prompt = context + f"""
You're interested but want a better deal. Based on your personality:
- Budget-conscious: Direct about price concerns
- Others: Might ask about extras or upgrades

Be realistic - don't be aggressive, just explore options.

Format as:
Subject: Re: {state.get('last_email_subject', 'Travel Proposal')}
[Email body]"""

    elif action == "make_decision":
        if state['interest_level'] > 0.7:
            prompt = context + """
You've decided to book! Write an email accepting their offer.
Show enthusiasm appropriate to your personality.
Ask about next steps.

Format as:
Subject: Re: {state.get('last_email_subject', 'Travel Proposal')} - Ready to Book!
[Email body]"""
        else:
            prompt = context + """
You've decided not to proceed. Write a polite decline.
Thank them for their time.
Leave the door open if interest level is moderate.

Format as:
Subject: Re: {state.get('last_email_subject', 'Travel Proposal')} 
[Email body]"""

    elif action == "send_correction":
        forgotten = state['forgot_to_mention'][0] if state['forgot_to_mention'] else "important detail"
        prompt = context + f"""
You just remembered you forgot to mention: {forgotten}

Write a follow-up email mentioning this naturally.
Apologize briefly but don't overdo it.

Format as:
Subject: Re: {state.get('last_email_subject', 'Travel Inquiry')} - One more thing
[Email body]"""

    else:  # abandon
        prompt = context + """
You've decided to end the conversation. Write a brief, polite email.

Format as:
Subject: Re: {state.get('last_email_subject', 'Travel Inquiry')}
[Email body]"""

    # Generate email with LLM
    response = llm.generate_content(prompt)
    
    # Parse response to extract subject and body
    lines = response.text.strip().split('\n')
    subject = ""
    body_lines = []
    
    for i, line in enumerate(lines):
        if line.startswith("Subject:"):
            subject = line.replace("Subject:", "").strip()
        elif i > 0:  # Skip until after subject line
            body_lines.append(line)
    
    body = '\n'.join(body_lines).strip()
    
    # Update state based on action
    if action == "initial_inquiry":
        state["shared_info"]["destination_shared"] = True
        state["phase"] = "exploring"
    
    elif action == "provide_details":
        # Mark randomly what was shared based on response content
        if "budget" in body.lower() or "$" in body:
            state["shared_info"]["budget_shared"] = True
        if "travel" in body.lower() and any(word in body.lower() for word in ["july", "august", "summer", "month"]):
            state["shared_info"]["dates_shared"] = True
        if any(word in body.lower() for word in ["family", "solo", "couple", "group", "children"]):
            state["shared_info"]["group_size_shared"] = True
    
    elif action == "express_interest":
        state["interest_level"] = min(state["interest_level"] + 0.2, 0.9)
        state["phase"] = "interested"
    
    elif action == "raise_concern":
        if state["concerns"]:
            state["concerns"].pop(0)
        state["abandonment_risk"] = max(state["abandonment_risk"] - 0.1, 0)
    
    elif action == "negotiate":
        state["phase"] = "deciding"
    
    elif action == "make_decision":
        if state["interest_level"] > 0.7:
            state["ready_to_book"] = True
            state["phase"] = "booking"
        else:
            state["phase"] = "done"
    
    elif action == "send_correction":
        if state["forgot_to_mention"]:
            item = state["forgot_to_mention"].pop(0)
            state["important_points"].append(item)
            state["shared_info"]["special_requirements_shared"] = True
    
    elif action == "abandon":
        state["phase"] = "done"
    
    # Store the email
    state["messages"].append({
        "role": "client",
        "content": body,
        "subject": subject
    })
    state["last_email_subject"] = subject
    
    return {"subject": subject, "body": body, "state": state}


def get_client_action(state: ClientState, llm) -> str:
    """Use LLM to intelligently decide next action"""
    
    # Build context about conversation flow
    conversation_summary = "No messages yet"
    if state["messages"]:
        recent_msgs = state["messages"][-3:]  # Last 3 messages
        conversation_summary = "\n".join([
            f"{msg['role']}: {msg['content'][:100]}..." for msg in recent_msgs
        ])
    
    prompt = f"""You are an AI orchestrating a travel client's email behavior.

Client Profile:
- Name: {state['persona_name']}
- Personality: {state['persona_data'].get('personality')}
- Decision style: {state['persona_data'].get('decision_style')}
- Current phase: {state['phase']}
- Interest level: {state['interest_level']:.1f}/1.0
- Abandonment risk: {state['abandonment_risk']:.1f}/1.0

Recent conversation:
{conversation_summary}

Information tracking:
- Still has {len(state['concerns'])} concerns
- Forgot to mention {len(state['forgot_to_mention'])} things
- Shared: {sum(state['shared_info'].values())}/{len(state['shared_info'])} key details

Available actions:
1. provide_details - Share more trip information
2. express_interest - React positively to proposal  
3. raise_concern - Ask about worries
4. negotiate - Try for better pricing/terms
5. make_decision - Accept or decline offer
6. send_correction - Remember forgotten details
7. abandon - Leave if not interested

Analyze the conversation flow and client's personality to decide the most realistic next action.
Consider:
- Has the agency addressed their concerns?
- Is it time to share forgotten details?
- Would this personality negotiate or just accept?
- Are they genuinely interested or just being polite?

Return ONLY the action name."""

    response = llm.generate_content(prompt)
    action = response.text.strip().lower().replace(" ", "_")
    
    # Validate action
    valid_actions = ["provide_details", "express_interest", "raise_concern",
                    "negotiate", "make_decision", "send_correction", "abandon"]
    
    if action not in valid_actions:
        # Smart fallback
        if not state["messages"]:
            return "provide_details"
        elif state["concerns"] and random.random() > 0.5:
            return "raise_concern"
        elif state["forgot_to_mention"] and len(state["messages"]) > 4:
            return "send_correction"
        elif state["interest_level"] > 0.7:
            return "make_decision"
        elif state["abandonment_risk"] > 0.6:
            return "abandon"
        else:
            return "express_interest"
    
    return action