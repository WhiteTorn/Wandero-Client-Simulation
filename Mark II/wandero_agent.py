from typing import Dict, List
from datetime import datetime, timedelta
import random
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from graph_state import ConversationState, EmailMessage
import re
import time

class WanderoAgent:
    def __init__(self, company_data: Dict, llm: ChatGoogleGenerativeAI):
        self.company_data = company_data
        self.llm = llm
        self.agent_name = random.choice(["Maria Rodriguez", "Carlos Mendez", "Sofia Vargas"])
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the Wandero agent graph"""
        workflow = StateGraph(ConversationState)
        
        # Add nodes
        workflow.add_node("send_introduction", self.send_introduction)
        workflow.add_node("gather_all_details", self.gather_all_details)
        workflow.add_node("present_proposal", self.present_proposal)
        workflow.add_node("handle_negotiation", self.handle_negotiation)
        workflow.add_node("close_deal", self.close_deal)
        workflow.add_node("accept_decline", self.accept_decline)
        
        # REMOVE ALL CONFLICTING UNCONDITIONAL EDGES
        # These were causing the infinite loop by conflicting with conditional routing
        
        # Create a single routing function that handles all transitions
        def route_wandero_action(state: ConversationState) -> str:
            """Route to appropriate Wandero action based on state"""
            
            # If conversation is ended, finish
            if state.get("conversation_ended"):
                return "END"
            
            # If this is the first interaction, send introduction
            if not state.get("messages"):
                return "send_introduction"
                
            # Check if we just sent introduction - move to gathering details
            if state["phase"] == "introduction":
                return "gather_all_details"
                
            # If we don't have all info, keep gathering
            if not state.get("all_info_gathered"):
                return "gather_all_details"
                
            # If we have all info but haven't sent proposal, send it
            if state.get("all_info_gathered") and state["phase"] == "discovery":
                return "present_proposal"
                
            # Handle client responses to proposal
            if state["phase"] == "proposal":
                return "handle_negotiation"
                
            # Continue negotiation
            if state["phase"] == "negotiation":
                # Check if client wants to book or decline
                if state.get("ready_to_book"):
                    return "close_deal"
                else:
                    return "handle_negotiation"
            
            # Handle final decisions
            if state.get("ready_to_book"):
                return "close_deal"
            elif state.get("conversation_ended"):
                return "accept_decline"
            else:
                return "handle_negotiation"
        
        # Add conditional routing from ALL nodes
        for node in ["send_introduction", "gather_all_details", "present_proposal", 
                    "handle_negotiation", "close_deal", "accept_decline"]:
            workflow.add_conditional_edges(
                node,
                route_wandero_action,
                {
                    "send_introduction": "send_introduction",
                    "gather_all_details": "gather_all_details", 
                    "present_proposal": "present_proposal",
                    "handle_negotiation": "handle_negotiation",
                    "close_deal": "close_deal",
                    "accept_decline": "accept_decline",
                    "END": END
                }
            )
        
        workflow.set_entry_point("send_introduction")
        
        return workflow.compile()
    
    def _route_after_intro(self, state: ConversationState) -> str:
        """Determine next action after introduction"""
        if not state.get("all_info_gathered"):
            return "gather_details"
        return "end"
    
    def send_introduction(self, state: ConversationState) -> ConversationState:
        """Send initial introduction email"""
        prompt = f"""
        You are {self.agent_name} from {self.company_data['name']}.
        
        Company profile:
        - Type: {self.company_data.get('type')}
        - Specialties: {', '.join(self.company_data.get('specialties', []))}
        - Unique points: {', '.join(self.company_data.get('unique_selling_points', [])[:2])}
        
        Write a welcoming introduction email that:
        1. Introduces yourself and the company
        2. Highlights what makes you special (based on company type)
        3. Shows enthusiasm about Chile
        4. Asks for their travel details (dates, budget, group size, interests)
        5. Keeps it professional but warm
        
        Format:
        Subject: Welcome to {self.company_data['name']} - Your Chilean Adventure Awaits!
        Body: [professional email with signature]
        """
        time.sleep(10)
        response = self.llm.invoke(prompt).content
        subject, body = self._parse_email_response(response)
        
        email = EmailMessage(
            subject=subject,
            body=body,
            sender=f"{self.agent_name} <{self.company_data['name']}>",
            timestamp=state.get("current_time", datetime.now()),
            sentiment=0.8
        )
        
        state["messages"] = [email]  # First message
        state["phase"] = "introduction"  # Change this to introduction instead of discovery
        state["agent_name"] = self.agent_name
        state["company_name"] = self.company_data['name']
        state["company_type"] = self.company_data.get('type', 'standard')
        
        return state
    
    def gather_all_details(self, state: ConversationState) -> ConversationState:
        """Ask for ALL missing details at once"""
        # Check what we still need
        missing = []
        if not state.get("client_budget"):
            missing.append("budget range")
        if not state.get("client_travel_dates"):
            missing.append("preferred travel dates")
        if not state.get("client_group_size"):
            missing.append("number of travelers")
        if not state.get("client_interests") or len(state["client_interests"]) == 0:
            missing.append("specific interests or must-see places")
            
        if not missing:
            state["all_info_gathered"] = True
            return state
        
        # Get last client message
        last_client_msg = ""
        for msg in reversed(state["messages"]):
            if msg["sender"] == state["client_name"]:
                last_client_msg = msg["body"]
                break
        
        prompt = f"""
        You are {state['agent_name']} from {state['company_name']}.
        
        Client's last message:
        "{last_client_msg}"
        
        You need to gather these missing details efficiently:
        {', '.join(missing)}
        
        Write a friendly but efficient email that:
        1. Acknowledges what they've shared
        2. Asks for ALL missing information in one go
        3. Explains why you need each piece of info
        4. Keeps it concise and organized
        
        Format:
        Subject: Re: [previous subject]
        Body: [organized email asking for all details]
        """
        time.sleep(10)
        response = self.llm.invoke(prompt).content
        subject, body = self._parse_email_response(response)
        
        # Calculate response time (1-2 hours during business hours)
        response_delay = timedelta(hours=random.uniform(1, 2))
        
        email = EmailMessage(
            subject=subject,
            body=body,
            sender=f"{state['agent_name']} <{state['company_name']}>",
            timestamp=state.get("current_time", datetime.now()) + response_delay,
            sentiment=0.7
        )
        
        state["messages"].append(email)
        state["last_wandero_response_time"] = email["timestamp"]
        
        return state
    
    def present_proposal(self, state: ConversationState) -> ConversationState:
        """Present a comprehensive proposal based on all gathered info"""
        # Build proposal based on company type and client needs
        if self.company_data.get('type') == 'luxury':
            base_price = 800
            package_name = "Exclusive Chile Experience"
        elif self.company_data.get('type') == 'adventure':
            base_price = 350
            package_name = "Chile Adventure Expedition"
        elif self.company_data.get('type') == 'family':
            base_price = 450
            package_name = "Family Chile Discovery"
        else:
            base_price = 300
            package_name = "Classic Chile Journey"
            
        # Adjust for group size
        group_size = self._extract_group_size(state.get("client_group_size", "solo"))
        total_price = base_price * group_size * 7  # Assume 7-day trip
        
        prompt = f"""
        You are {state['agent_name']} presenting a detailed proposal.
        
        Client details:
        - Name: {state['client_name']}
        - Budget: ${state.get('client_budget', {}).get('min', 0)}-${state.get('client_budget', {}).get('max', 0)}
        - Dates: {state.get('client_travel_dates', 'flexible')}
        - Group: {state.get('client_group_size', 'solo')}
        - Interests: {', '.join(state.get('client_interests', []))}
        
        Create a detailed proposal for "{package_name}":
        - Base price: ${base_price}/person/day
        - Total estimated: ${total_price}
        - Duration: 7 days/6 nights
        
        Include:
        1. Specific itinerary highlights matching their interests
        2. Accommodation details
        3. What's included/excluded
        4. Clear pricing breakdown
        5. Value propositions
        
        Make it visual and exciting but honest about pricing.
        
        Format:
        Subject: Your Personalized {package_name} Proposal
        Body: [detailed, well-formatted proposal]
        """
        
        time.sleep(10)
        response = self.llm.invoke(prompt).content
        subject, body = self._parse_email_response(response)
        
        # Store proposal
        proposal = {
            "name": package_name,
            "base_price": base_price,
            "total_price": total_price,
            "duration": "7 days/6 nights"
        }
        state["proposals_made"] = [proposal]
        state["current_offer"] = proposal
        
        # Quick response for proposals (30-60 min)
        response_delay = timedelta(minutes=random.uniform(30, 60))
        
        email = EmailMessage(
            subject=subject,
            body=body,
            sender=f"{state['agent_name']} <{state['company_name']}>",
            timestamp=state.get("current_time", datetime.now()) + response_delay,
            sentiment=0.8
        )
        
        state["messages"].append(email)
        state["phase"] = "proposal"
        state["last_wandero_response_time"] = email["timestamp"]
        
        return state
    
    def handle_negotiation(self, state: ConversationState) -> ConversationState:
        """Handle price negotiations or concerns"""
        # Analyze client's concern
        last_client_msg = ""
        for msg in reversed(state["messages"]):
            if msg["sender"] == state["client_name"]:
                last_client_msg = msg["body"].lower()
                break
                
        # Determine response type
        if "price" in last_client_msg or "expensive" in last_client_msg or "budget" in last_client_msg:
            response_type = "price_concern"
        elif "safety" in last_client_msg or "safe" in last_client_msg:
            response_type = "safety_concern"
        else:
            response_type = "general_concern"
            
        # Check if we can offer discount
        max_discount = self.company_data.get('max_discount', 0.15)
        can_discount = state.get("discounts_offered", 0) < max_discount
        
        if response_type == "price_concern" and can_discount:
            new_discount = min(0.1, max_discount - state.get("discounts_offered", 0))
            state["discounts_offered"] = state.get("discounts_offered", 0) + new_discount
            discount_text = f"special {int(new_discount * 100)}% discount"
        else:
            discount_text = "our best value options"
            
        prompt = f"""
        You are {state['agent_name']} addressing client concerns.
        
        Client concern type: {response_type}
        Their message: "{last_client_msg}"
        
        Company type: {self.company_data.get('type')}
        Can offer discount: {can_discount}
        Discount to offer: {discount_text}
        
        Write a response that:
        1. Addresses their specific concern thoroughly
        2. {"Offers the discount if price is the issue" if can_discount else "Explains the value"}
        3. Reassures without being pushy
        4. Creates gentle urgency if offering discount
        
        Be understanding and professional.
        
        Format:
        Subject: Re: [previous subject]
        Body: [response addressing concerns]
        """
        time.sleep(10)
        response = self.llm.invoke(prompt).content
        subject, body = self._parse_email_response(response)
        
        # Quick response to concerns (1-2 hours)
        response_delay = timedelta(hours=random.uniform(1, 2))
        
        email = EmailMessage(
            subject=subject,
            body=body,
            sender=f"{state['agent_name']} <{state['company_name']}>",
            timestamp=state.get("current_time", datetime.now()) + response_delay,
            sentiment=0.7
        )
        
        state["messages"].append(email)
        state["phase"] = "negotiation"
        state["last_wandero_response_time"] = email["timestamp"]
        
        return state
    
    def close_deal(self, state: ConversationState) -> ConversationState:
        """Send booking confirmation"""
        prompt = f"""
        You are {state['agent_name']} sending a booking confirmation.
        
        The client has agreed to book {state['current_offer']['name']}.
        
        Write an enthusiastic confirmation email that:
        1. Expresses genuine excitement
        2. Confirms key details
        3. Lists clear next steps
        4. Provides payment instructions
        5. Gives your direct contact info
        6. Makes them feel great about their decision
        
        Format:
        Subject: 🎉 Booking Confirmed - Your {state['current_offer']['name']} Adventure!
        Body: [warm confirmation email with all details]
        """
        time.sleep(10)
        response = self.llm.invoke(prompt).content
        subject, body = self._parse_email_response(response)
        
        # Very quick response for confirmations (15-30 min)
        response_delay = timedelta(minutes=random.uniform(15, 30))
        
        email = EmailMessage(
            subject=subject,
            body=body,
            sender=f"{state['agent_name']} <{state['company_name']}>",
            timestamp=state.get("current_time", datetime.now()) + response_delay,
            sentiment=0.9
        )
        
        state["messages"].append(email)
        state["phase"] = "closing"
        state["conversation_ended"] = True
        
        return state
    
    def accept_decline(self, state: ConversationState) -> ConversationState:
        """Gracefully accept client's decision to not book"""
        prompt = f"""
        You are {state['agent_name']} from {state['company_name']}, a CHILE TRAVEL AGENCY.
        
        The client has decided not to book their Chile trip at this time.
        
        Write a gracious closing email that:
        1. Thanks them for considering Chile as a destination
        2. Leaves the door open for future travel
        3. Offers to help when they're ready
        4. Mentions Chile specifically
        5. Stays professional and warm
        
        This is about TRAVEL, not event planning!
        
        Format:
        Subject: Re: Your Chile Travel Inquiry
        Body: [brief, gracious closing about their Chile travel plans]
        """
        time.sleep(10)
        response = self.llm.invoke(prompt).content
        subject, body = self._parse_email_response(response)
        
        # Fallback if LLM fails
        if not body.strip() or "event" in body.lower():
            body = f"""Dear {state['client_name']},

    Thank you so much for considering {state['company_name']} for your Chile adventure. I understand that now might not be the right time for your trip.

    Please know that whenever you're ready to explore the wonders of Chile - from the Atacama Desert to Patagonia - I'll be here to help create your perfect journey.

    Feel free to reach out anytime if you have questions or when you're ready to start planning.

    Wishing you all the best!

    Warm regards,
    {state['agent_name']}
    {state['company_name']}"""
        
        response_delay = timedelta(hours=random.uniform(2, 4))
        
        email = EmailMessage(
            subject=subject,
            body=body,
            sender=f"{state['agent_name']} <{state['company_name']}>",
            timestamp=state.get("current_time", datetime.now()) + response_delay,
            sentiment=0.6
        )
        
        state["messages"].append(email)
        state["phase"] = "abandoned"
        state["conversation_ended"] = True
        
        return state
    
    def _extract_group_size(self, group_description: str) -> int:
        """Extract numeric group size from description"""
        if "solo" in group_description.lower():
            return 1
        elif "couple" in group_description.lower() or "two" in group_description.lower():
            return 2
        elif "family" in group_description.lower():
            return 4  # Assume family of 4
        else:
            # Try to extract number
            numbers = re.findall(r'\d+', group_description)
            return int(numbers[0]) if numbers else 1
    
    def _parse_email_response(self, response: str) -> tuple[str, str]:
        """Parse LLM response into subject and body"""
        lines = response.strip().split('\n')
        subject = "Re: Your Chile Travel Inquiry"
        body_lines = []
        
        in_body = False
        for line in lines:
            if line.startswith("Subject:"):
                subject = line.replace("Subject:", "").strip()
            elif line.startswith("Body:"):
                in_body = True
            elif in_body or (subject != "Re: Your Chile Travel Inquiry" and not line.startswith("Subject:")):
                body_lines.append(line)
        
        body = '\n'.join(body_lines).strip()
        return subject, body
    
    # Add these methods to WanderoAgent class

    def handle_price_discussion(self, state: ConversationState) -> ConversationState:
        """Handle specific price-related questions"""
        # Get client's concern
        last_client_msg = ""
        for msg in reversed(state["messages"]):
            if msg["sender"] == state["client_name"]:
                last_client_msg = msg["body"]
                break
        
        # Extract their budget concern
        client_budget_max = state.get("client_budget", {}).get("max", 0)
        current_price = state.get("current_offer", {}).get("total_price", 0)
        
        # Check if we can work with their budget
        if current_price > client_budget_max * 1.2:  # More than 20% over
            # Too far apart
            can_work = False
            suggestion = "alternative budget-friendly options"
        else:
            # Can potentially work
            can_work = True
            max_discount = self.company_data.get('max_discount', 0.15)
            
        prompt = f"""
        You are {state['agent_name']} from {state['company_name']} discussing pricing for CHILE travel.
        
        Client's message: "{last_client_msg}"
        
        Current package price: ${current_price}
        Client's budget: up to ${client_budget_max}
        Can offer discount: {can_work}
        Max discount available: {max_discount * 100}%
        
        Write a helpful response that:
        1. Acknowledges their budget concern
        2. {"Offers a discount or payment plan" if can_work else "Suggests this might not be the right fit"}
        3. Shows enthusiasm about helping them visit Chile
        4. Keeps the conversation going if they're interested
        
        Be understanding and solution-oriented.
        
        Format:
        Subject: Re: Your Chile Adventure - Let's Make It Work!
        Body: [helpful response about pricing]
        """
        time.sleep(10)
        response = self.llm.invoke(prompt).content
        subject, body = self._parse_email_response(response)
        
        # Apply discount if offered
        if can_work and state.get("discounts_offered", 0) < max_discount:
            state["discounts_offered"] = min(0.1, max_discount)
        
        response_delay = timedelta(minutes=random.uniform(20, 40))  # Quick response for price concerns
        
        email = EmailMessage(
            subject=subject,
            body=body,
            sender=f"{state['agent_name']} <{state['company_name']}>",
            timestamp=state.get("last_client_response_time") or state.get("current_time") or datetime.now() + response_delay,
            sentiment=0.7
        )
        
        state["messages"].append(email)
        state["last_wandero_response_time"] = email["timestamp"]
        
        return state

    def address_authenticity_concerns(self, state: ConversationState) -> ConversationState:
        """Address concerns about authentic vs touristy experiences"""
        last_client_msg = ""
        for msg in reversed(state["messages"]):
            if msg["sender"] == state["client_name"]:
                last_client_msg = msg["body"]
                break
        
        prompt = f"""
        You are {state['agent_name']} from {state['company_name']} addressing concerns about authentic experiences in CHILE.
        
        Client said: "{last_client_msg}"
        
        They want authentic, local experiences and are worried about tourist traps.
        Company type: {self.company_data.get('type')}
        
        Write a response that:
        1. Shows you understand their desire for authenticity
        2. Explains how your packages include authentic local experiences
        3. Mentions specific examples of non-touristy activities in Chile
        4. Reassures them while staying true to your company type
        
        IMPORTANT: Talk about CHILE, not generic "[Destination Name]"
        
        Format:
        Subject: Re: Authentic Chilean Experiences - Absolutely!
        Body: [reassuring response about authentic Chile travel]
        """
        time.sleep(10)
        response = self.llm.invoke(prompt).content
        subject, body = self._parse_email_response(response)
        
        response_delay = timedelta(minutes=random.uniform(30, 60))
        
        email = EmailMessage(
            subject=subject,
            body=body,
            sender=f"{state['agent_name']} <{state['company_name']}>",
            timestamp=state.get("last_client_response_time") or state.get("current_time") or datetime.now() + response_delay,
            sentiment=0.8
        )
        
        state["messages"].append(email)
        state["last_wandero_response_time"] = email["timestamp"]
        
        return state

    def handle_negotiation(self, state: ConversationState) -> ConversationState:
        """Handle general negotiation or questions - TRAVEL focused"""
        last_client_msg = ""
        for msg in reversed(state["messages"]):
            if msg["sender"] == state["client_name"]:
                last_client_msg = msg["body"]
                break
        
        # Make sure we stay in travel context
        prompt = f"""
        You are {state['agent_name']} from {state['company_name']}, a TRAVEL AGENCY specializing in CHILE.
        
        Client's message: "{last_client_msg}"
        
        This is a conversation about TRAVEL TO CHILE, not event planning or any other service.
        The client is interested (interest level: {state['interest_level']}) and asking questions.
        
        Write a helpful response that:
        1. Addresses their specific questions or concerns
        2. Stays focused on CHILE TRAVEL
        3. Keeps the conversation moving forward
        4. Shows enthusiasm about their trip
        
        DO NOT mention event planning, meetings, or any non-travel topics.
        
        Format:
        Subject: Re: Your Chile Adventure
        Body: [response focused on their Chile travel plans]
        """
        time.sleep(10)
        response = self.llm.invoke(prompt).content
        subject, body = self._parse_email_response(response)
        
        response_delay = timedelta(hours=random.uniform(1, 2))
        
        email = EmailMessage(
            subject=subject,
            body=body,
            sender=f"{state['agent_name']} <{state['company_name']}>",
            timestamp=state.get("last_client_response_time") or state.get("current_time") or datetime.now() + response_delay,
            sentiment=0.7
        )
        
        state["messages"].append(email)
        state["last_wandero_response_time"] = email["timestamp"]
        
        return state

    # Update the accept_decline method to be more appropriate
    def accept_decline(self, state: ConversationState) -> ConversationState:
        """Gracefully accept client's decision to not book"""
        prompt = f"""
        You are {state['agent_name']} from {state['company_name']}, a CHILE TRAVEL AGENCY.
        
        The client has decided not to book their Chile trip at this time.
        
        Write a gracious closing email that:
        1. Thanks them for considering Chile as a destination
        2. Leaves the door open for future travel
        3. Offers to help when they're ready
        4. Mentions Chile specifically
        5. Stays professional and warm
        
        This is about TRAVEL, not event planning!
        
        Format:
        Subject: Re: Your Chile Travel Inquiry
        Body: [brief, gracious closing about their Chile travel plans]
        """
        time.sleep(10)
        response = self.llm.invoke(prompt).content
        subject, body = self._parse_email_response(response)
        
        # Fallback if LLM fails
        if not body.strip() or "event" in body.lower():
            body = f"""Dear {state['client_name']},

    Thank you so much for considering {state['company_name']} for your Chile adventure. I understand that now might not be the right time for your trip.

    Please know that whenever you're ready to explore the wonders of Chile - from the Atacama Desert to Patagonia - I'll be here to help create your perfect journey.

    Feel free to reach out anytime if you have questions or when you're ready to start planning.

    Wishing you all the best!

    Warm regards,
    {state['agent_name']}
    {state['company_name']}"""
        
        response_delay = timedelta(hours=random.uniform(2, 4))
        
        email = EmailMessage(
            subject=subject,
            body=body,
            sender=f"{state['agent_name']} <{state['company_name']}>",
            timestamp=state.get("last_client_response_time") or state.get("current_time") or datetime.now() + response_delay,
            sentiment=0.6
        )
        
        state["messages"].append(email)
        state["phase"] = "abandoned"
        state["conversation_ended"] = True
        
        return state