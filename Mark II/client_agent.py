from typing import Dict, List
from datetime import datetime, timedelta
import random
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from graph_state import ConversationState, EmailMessage
import re

class ClientAgent:
    def __init__(self, persona_data: Dict, llm: ChatGoogleGenerativeAI):
        self.persona_data = persona_data
        self.llm = llm
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the client agent graph"""
        workflow = StateGraph(ConversationState)
        
        # Add nodes
        workflow.add_node("analyze_situation", self.analyze_situation)
        workflow.add_node("compose_initial_inquiry", self.compose_initial_inquiry)
        workflow.add_node("provide_all_details", self.provide_all_details)
        workflow.add_node("respond_to_proposal", self.respond_to_proposal)
        workflow.add_node("negotiate_or_decide", self.negotiate_or_decide)
        workflow.add_node("send_final_decision", self.send_final_decision)
        workflow.add_node("remember_forgotten_detail", self.remember_forgotten_detail)

        # Fix: Create a proper routing function that returns the node name directly
        def route_after_analysis(state: ConversationState) -> str:
            """Route based on conversation state"""
            if not state.get("messages"):
                return "compose_initial_inquiry"
            
            last_message = state["messages"][-1]
            
            # Check if we forgot something important
            if state.get("client_special_requirements") and random.random() > 0.7:
                forgotten_items = [req for req in state["client_special_requirements"] 
                                 if req not in str(state["messages"])]
                if forgotten_items and len(state["messages"]) > 3:
                    return "remember_forgotten_detail"
            
            # Route based on conversation phase
            if state["phase"] == "introduction":
                return "compose_initial_inquiry"
            elif state["phase"] == "discovery" and not state["all_info_gathered"]:
                return "provide_all_details"
            elif state["phase"] == "proposal":
                return "respond_to_proposal"
            elif state["phase"] == "negotiation":
                return "negotiate_or_decide"
            else:
                return "send_final_decision"

        # Fix: Use the local function instead of self method
        workflow.add_conditional_edges(
            "analyze_situation", 
            route_after_analysis,
            # Remove the mapping dict - let LangGraph use the direct return values
        )
        
        # Add edges with conditions
        workflow.add_edge("compose_initial_inquiry", END)
        workflow.add_edge("provide_all_details", END)
        workflow.add_edge("respond_to_proposal", END)
        workflow.add_edge("negotiate_or_decide", END)
        workflow.add_edge("send_final_decision", END)
        workflow.add_edge("remember_forgotten_detail", END)
        
        # Set entry point
        workflow.set_entry_point("analyze_situation")
        
        return workflow.compile()
    
    def analyze_situation(self, state: ConversationState) -> ConversationState:
        """Analyze current situation and update client understanding"""
        if state.get("messages"):
            last_wandero_msg = None
            for msg in reversed(state["messages"]):
                if msg["sender"] != state["client_name"]:
                    last_wandero_msg = msg
                    break
            
            if last_wandero_msg:
                # Analyze sentiment
                sentiment_prompt = f"""
                Analyze the sentiment of this email from a travel agency:
                "{last_wandero_msg['body']}"
                
                Rate from -1 (very negative) to 1 (very positive).
                Consider: helpfulness, enthusiasm, addressing concerns, pricing clarity.
                Return ONLY a number.
                """
                
                try:
                    sentiment = float(self.llm.invoke(sentiment_prompt).content.strip())
                    state["interest_level"] = max(0, min(1, state["interest_level"] + sentiment * 0.2))
                except:
                    pass
        
        # Update response timing based on interest and personality
        if state.get("last_wandero_response_time"):
            base_delay = self._calculate_response_delay(state)
            state["current_time"] = state["last_wandero_response_time"] + base_delay
        
        return state
    
    def compose_initial_inquiry(self, state: ConversationState) -> ConversationState:
        """Compose first email with some but not all details"""
        prompt = f"""
        You are {self.persona_data['name']} writing your FIRST email to a travel agency.
        
        Your profile:
        - Personality: {self.persona_data.get('personality', 'standard')}
        - Interests: {', '.join(self.persona_data.get('interests', []))}
        - Travel style: {self.persona_data.get('decision_style', 'standard')}
        
        Write a natural initial inquiry that:
        1. Mentions your interest in Chile
        2. Shares 1-2 key details (but NOT everything)
        3. Asks a general question
        4. Matches your personality (cautious = formal, spontaneous = casual)
        
        DO NOT share all details at once - save budget, dates, special requirements for later.
        
        Format:
        Subject: [subject line]
        Body: [email body with appropriate greeting and sign-off]
        """
        
        response = self.llm.invoke(prompt).content
        subject, body = self._parse_email_response(response)
        
        # Create email
        email = EmailMessage(
            subject=subject,
            body=body,
            sender=state["client_name"],
            timestamp=state["current_time"],
            sentiment=0.5
        )
        
        state["messages"].append(email)
        
        # Update what we shared
        if "chile" in body.lower():
            state["client_interests"] = self.persona_data.get('interests', [])
        
        return state
    
    def provide_all_details(self, state: ConversationState) -> ConversationState:
        """Provide comprehensive details when asked"""
        # Gather what hasn't been shared
        unshared_info = []
        
        if not state.get("client_budget"):
            budget = self.persona_data.get('budget', {})
            unshared_info.append(f"Budget: ${budget.get('min', 1000)}-${budget.get('max', 2000)}")
            state["client_budget"] = budget
        
        if not state.get("client_travel_dates"):
            dates = self.persona_data.get('travel_dates', 'flexible')
            unshared_info.append(f"Travel dates: {dates}")
            state["client_travel_dates"] = dates
            
        if not state.get("client_group_size"):
            group = self.persona_data.get('travel_group', 'solo')
            unshared_info.append(f"Group: {group}")
            state["client_group_size"] = group
        
        # Get last Wandero message
        last_wandero_msg = ""
        for msg in reversed(state["messages"]):
            if msg["sender"] != state["client_name"]:
                last_wandero_msg = msg["body"]
                break
        
        prompt = f"""
        You are {state['client_name']} responding to the travel agency.
        
        Their last email asked for more information:
        "{last_wandero_msg}"
        
        Provide these details naturally:
        {chr(10).join(unshared_info)}
        
        Also mention your interests: {', '.join(self.persona_data.get('interests', []))}
        
        Keep the tone consistent with {self.persona_data.get('personality', 'standard')} personality.
        
        Format:
        Subject: Re: [previous subject]
        Body: [email responding with all requested information]
        """
        
        response = self.llm.invoke(prompt).content
        subject, body = self._parse_email_response(response)
        
        email = EmailMessage(
            subject=subject,
            body=body,
            sender=state["client_name"],
            timestamp=state["current_time"],
            sentiment=0.6
        )
        
        state["messages"].append(email)
        state["all_info_gathered"] = True
        
        return state
    
    def respond_to_proposal(self, state: ConversationState) -> ConversationState:
        """Respond to a travel proposal"""
        # Extract proposal details from last message
        last_msg = state["messages"][-1]["body"]
        
        # Check if proposal fits budget
        budget_ok = True
        if "$" in last_msg:
            prices = re.findall(r'\$(\d+)', last_msg)
            if prices:
                max_price = max(int(p) for p in prices)
                if state.get("client_budget"):
                    budget_ok = max_price <= state["client_budget"].get("max", 10000)
        
        # Generate response based on personality and budget fit
        if self.persona_data.get('personality') == 'budget-conscious' and not budget_ok:
            sentiment = "concerned about the price"
            state["interest_level"] *= 0.7
        elif self.persona_data.get('personality') == 'spontaneous':
            sentiment = "excited but want to know more"
            state["interest_level"] = min(state["interest_level"] + 0.2, 0.9)
        else:
            sentiment = "interested but have questions"
        
        prompt = f"""
        You are {state['client_name']} responding to a travel proposal.
        
        Personality: {self.persona_data.get('personality')}
        Your reaction: {sentiment}
        
        The proposal includes luxury services at high prices.
        Your budget is ${state.get('client_budget', {}).get('max', 2000)} max.
        
        Write a response that:
        1. Shows your reaction appropriately
        2. Asks about your main concern from: {self.persona_data.get('worries', [])}
        3. Hints at budget concerns if prices are too high
        
        Format:
        Subject: Re: [previous subject]
        Body: [natural response]
        """
        
        response = self.llm.invoke(prompt).content
        subject, body = self._parse_email_response(response)
        
        email = EmailMessage(
            subject=subject,
            body=body,
            sender=state["client_name"],
            timestamp=state["current_time"],
            sentiment=0.4 if not budget_ok else 0.7
        )
        
        state["messages"].append(email)
        state["phase"] = "negotiation"
        
        return state
    
    def negotiate_or_decide(self, state: ConversationState) -> ConversationState:
        """Negotiate or make a decision"""
        # Decision logic based on interest and personality
        if state["interest_level"] < 0.3:
            decision = "decline"
        elif state["interest_level"] > 0.7 and state.get("discounts_offered", 0) > 0:
            decision = "accept"
        else:
            decision = "negotiate" if self.persona_data.get('personality') == 'budget-conscious' else "think"
        
        prompt = f"""
        You are {state['client_name']} making a decision about the trip.
        
        Decision: {decision}
        Interest level: {state['interest_level']}
        Personality: {self.persona_data.get('personality')}
        
        Write an email that:
        - {"Politely declines due to budget/fit" if decision == "decline" else ""}
        - {"Accepts the offer enthusiastically" if decision == "accept" else ""}
        - {"Tries to negotiate on price" if decision == "negotiate" else ""}
        - {"Asks for time to think" if decision == "think" else ""}
        
        Be natural and true to personality.
        
        Format:
        Subject: Re: [previous subject]
        Body: [decision email]
        """
        
        response = self.llm.invoke(prompt).content
        subject, body = self._parse_email_response(response)
        
        email = EmailMessage(
            subject=subject,
            body=body,
            sender=state["client_name"],
            timestamp=state["current_time"],
            sentiment=0.8 if decision == "accept" else 0.3
        )
        
        state["messages"].append(email)
        
        if decision in ["accept", "decline"]:
            state["conversation_ended"] = True
            state["ready_to_book"] = decision == "accept"
            
        return state
    
    def send_final_decision(self, state: ConversationState) -> ConversationState:
        """Send final decision email"""
        state["conversation_ended"] = True
        return state
    
    def remember_forgotten_detail(self, state: ConversationState) -> ConversationState:
        """Remember and mention forgotten requirements"""
        forgotten = random.choice(state["client_special_requirements"])
        
        prompt = f"""
        You are {state['client_name']} suddenly remembering an important detail.
        
        You forgot to mention: {forgotten}
        
        Write a brief follow-up email mentioning this naturally.
        Don't over-apologize, just mention it casually.
        
        Format:
        Subject: Re: [previous subject] - One more thing
        Body: [brief email mentioning the forgotten detail]
        """
        
        response = self.llm.invoke(prompt).content
        subject, body = self._parse_email_response(response)
        
        email = EmailMessage(
            subject=subject,
            body=body,
            sender=state["client_name"],
            timestamp=state["current_time"] + timedelta(minutes=30),
            sentiment=0.5
        )
        
        state["messages"].append(email)
        return state
    
    def _calculate_response_delay(self, state: ConversationState) -> timedelta:
        """Calculate realistic response time based on context"""
        base_hours = 3  # Base 3 hours
        
        # Personality factors
        if self.persona_data.get('personality') == 'spontaneous':
            base_hours *= 0.5  # Responds faster
        elif self.persona_data.get('personality') == 'cautious':
            base_hours *= 2  # Takes more time
            
        # Interest level factors
        if state["interest_level"] > 0.7:
            base_hours *= 0.7  # Responds faster when interested
        elif state["interest_level"] < 0.3:
            base_hours *= 1.5  # Slower when not interested
            
        # Time of day factors
        current_hour = state["current_time"].hour
        if current_hour >= 18:  # Evening
            base_hours += 12  # Responds next day
        elif current_hour >= 22:  # Late night
            base_hours += 14
            
        # Add randomness
        variance = base_hours * 0.3
        actual_hours = base_hours + random.uniform(-variance, variance)
        
        return timedelta(hours=max(0.5, actual_hours))
    
    def _parse_email_response(self, response: str) -> tuple[str, str]:
        """Parse LLM response into subject and body"""
        lines = response.strip().split('\n')
        subject = "Re: Travel Inquiry"
        body_lines = []
        
        for i, line in enumerate(lines):
            if line.startswith("Subject:"):
                subject = line.replace("Subject:", "").strip()
            elif line.startswith("Body:"):
                body_lines = lines[i+1:]
                break
            elif i > 0 and subject != "Re: Travel Inquiry":
                body_lines.append(line)
        
        body = '\n'.join(body_lines).strip()
        return subject, body