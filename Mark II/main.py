import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from pathlib import Path
import os
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
import google.generativeai as genai

from graph_state import ConversationState, EmailMessage
from client_agent import ClientAgent
from wandero_agent import WanderoAgent
from personas import PERSONAS
from companies import COMPANIES

load_dotenv()

delay = 7

class ConversationOrchestrator:
    def __init__(self, api_key: str):
        """Initialize orchestrator with LangGraph"""
        genai.configure(api_key=api_key)
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-lite",
            google_api_key=api_key
        )
        
        self.output_dir = Path("outputs")
        self.output_dir.mkdir(exist_ok=True)
        
    def create_conversation_graph(self, persona_data: Dict, company_data: Dict) -> StateGraph:
        """Create the main conversation graph"""
        # Initialize agents
        client_agent = ClientAgent(persona_data, self.llm)
        wandero_agent = WanderoAgent(company_data, self.llm)
        
        # Create main workflow
        workflow = StateGraph(ConversationState)
        
        # Add nodes
        workflow.add_node("wandero_turn", self._wandero_turn_wrapper(wandero_agent))
        workflow.add_node("client_turn", self._client_turn_wrapper(client_agent))
        workflow.add_node("check_end", self._check_conversation_end)
        
        # Add edges
        workflow.add_edge("wandero_turn", "check_end")
        workflow.add_edge("client_turn", "check_end")
        
        # Conditional routing from check_end
        workflow.add_conditional_edges(
            "check_end",
            self._route_conversation,
            {
                "continue_wandero": "wandero_turn",
                "continue_client": "client_turn",
                "end": END
            }
        )
        
        # Start with Wandero introduction
        workflow.set_entry_point("wandero_turn")
        
        return workflow.compile()
    
    def _wandero_turn_wrapper(self, agent: WanderoAgent):
        """Wrapper to run Wandero agent turn"""
        async def wandero_turn(state: ConversationState) -> ConversationState:
            # Determine Wandero action based on state

            await asyncio.sleep(delay)

            if not state.get("messages"):
                return agent.send_introduction(state)
            
            # Analyze last client message
            last_client_msg = None
            for msg in reversed(state["messages"]):
                if msg["sender"] == state["client_name"]:
                    last_client_msg = msg
                    break
                    
            if not last_client_msg:
                return state
            
            # Analyze client message content
            client_text = last_client_msg["body"].lower()
            
            # Check for specific scenarios
            if any(phrase in client_text for phrase in ["looking forward", "excited", "can't wait", "sounds amazing"]):
                # Client is interested - don't abandon!
                state["interest_level"] = max(state["interest_level"], 0.7)
            
            if any(word in client_text for word in ["goodbye", "not interested", "too expensive", "nevermind", "changed mind"]):
                # Clear rejection
                return agent.accept_decline(state)
            
            # Route based on conversation state
            if not state.get("all_info_gathered"):
                return agent.gather_all_details(state)
            elif state["phase"] == "discovery" and state.get("all_info_gathered"):
                return agent.present_proposal(state)
            elif state["phase"] in ["proposal", "negotiation"]:
                # Client responded to proposal - handle their concerns/questions
                if any(word in client_text for word in ["price", "cost", "budget", "expensive", "$"]):
                    return agent.handle_price_discussion(state)
                elif any(word in client_text for word in ["authentic", "local", "touristy", "real"]):
                    return agent.address_authenticity_concerns(state)
                else:
                    return agent.handle_negotiation(state)
            elif state.get("ready_to_book"):
                return agent.close_deal(state)
            else:
                # Default to continuing conversation
                return agent.handle_negotiation(state)
                
        return wandero_turn
    
    def _client_turn_wrapper(self, agent: ClientAgent):
        """Wrapper to run Client agent turn"""
        async def client_turn(state: ConversationState) -> ConversationState:
            # Run client agent graph
            await asyncio.sleep(delay)

            result = await agent.graph.ainvoke(state, {"recursion_limit": 25})
            await asyncio.sleep(delay)
            return result
            
        return client_turn
    
    def _check_conversation_end(self, state: ConversationState) -> ConversationState:
        """Check if conversation should end - be more conservative"""
        # Only end if explicitly ended
        if state.get("conversation_ended"):
            return state
            
        # Check message count - but higher limit
        if len(state.get("messages", [])) > 10:
            state["conversation_ended"] = True
            return state
            
        # Don't end based on interest if client is still engaged
        last_client_msg = None
        for msg in reversed(state.get("messages", [])):
            if msg["sender"] == state["client_name"]:
                last_client_msg = msg["body"].lower()
                break
        
        if last_client_msg:
            # Check for engagement signals
            engaged_phrases = ["looking forward", "excited", "sounds good", "tell me more", 
                            "what about", "can you", "how much", "when can"]
            if any(phrase in last_client_msg for phrase in engaged_phrases):
                # Client is engaged - don't end!
                return state
                
        # Only abandon if really low interest AND many messages
        if (state.get("interest_level", 0.5) < 0.2 and len(state.get("messages", [])) > 10):
            state["abandonment_risk"] = 0.9
            state["conversation_ended"] = True
            
        return state
    
    def _route_conversation(self, state: ConversationState) -> str:
        """Route to next agent or end"""
        if state.get("conversation_ended"):
            return "end"
            
        # Determine whose turn it is based on last message
        if not state.get("messages"):
            return "continue_wandero"
            
        last_sender = state["messages"][-1]["sender"]
        
        # Alternate turns
        if state.get("agent_name") in last_sender:
            return "continue_client"
        else:
            return "continue_wandero"
    
    async def run_conversation(self, persona_type: str, company_type: str) -> Dict:
        """Run a complete conversation"""
        print(f"\n{'='*80}")
        print(f"Starting Conversation: {persona_type} <-> {company_type}")
        print(f"{'='*80}\n")
        
        # Get data
        persona_data = PERSONAS.get(persona_type)
        company_data = COMPANIES.get(company_type)
        
        if not persona_data or not company_data:
            return {"error": "Invalid persona or company"}
            
        # Initialize state
        initial_state = ConversationState(
            messages=[],
            client_name=persona_data["name"],
            client_email=f"{persona_data['name'].lower().replace(' ', '.')}@email.com",
            client_personality=persona_data.get("personality", "standard"),
            client_budget=None,
            client_travel_dates=None,
            client_group_size=None,
            client_interests=[],
            client_concerns=persona_data.get("worries", []).copy(),
            client_special_requirements=persona_data.get("special_requirements", []).copy(),
            company_name="",
            company_type=company_data.get("type", "standard"),
            agent_name="",
            phase="introduction",
            interest_level=0.5,
            abandonment_risk=0.1,
            proposals_made=[],
            current_offer=None,
            discounts_offered=0.0,
            current_time=datetime.now().replace(hour=10, minute=0),  # Start at 10 AM
            last_client_response_time=None,
            last_wandero_response_time=None,
            all_info_gathered=False,
            ready_to_book=False,
            conversation_ended=False
        )
        await asyncio.sleep(delay)
        # Create and run graph
        graph = self.create_conversation_graph(persona_data, company_data)
        
        # Run conversation
        final_state = await graph.ainvoke(initial_state, {"recursion_limit": 25})
        await asyncio.sleep(delay)
        # Display conversation
        self._display_conversation(final_state)
        await asyncio.sleep(delay)
        # Generate summary
        summary = self._generate_summary(persona_type, company_type, final_state)
        await asyncio.sleep(delay)
        # Save results
        self._save_conversation(persona_type, company_type, final_state, summary)
        await asyncio.sleep(delay)
        return summary
    
    def _display_conversation(self, state: ConversationState):
        """Display the email conversation"""
        print("\n📧 EMAIL CONVERSATION THREAD\n")
        
        for i, msg in enumerate(state["messages"]):
            print(f"\n{'='*70}")
            print(f"Email #{i+1}")
            print(f"From: {msg['sender']}")
            print(f"Time: {msg['timestamp'].strftime('%Y-%m-%d %H:%M')}")
            print(f"Subject: {msg['subject']}")
            print(f"{'-'*70}")
            print(msg['body'])
            print(f"{'='*70}")
            
            # Show time delay to next message
            if i < len(state["messages"]) - 1:
                next_msg = state["messages"][i + 1]
                time_diff = next_msg["timestamp"] - msg["timestamp"]
                hours = time_diff.total_seconds() / 3600
                print(f"\n⏱️  {hours:.1f} hours later...")
    
    def _generate_summary(self, persona_type: str, company_type: str, 
                         state: ConversationState) -> Dict:
        """Generate conversation summary"""
        messages = state.get("messages", [])
        
        # Determine outcome
        if state.get("ready_to_book"):
            outcome = "BOOKING_CONFIRMED"
        elif state.get("conversation_ended") and state.get("interest_level", 0) < 0.4:
            outcome = "CLIENT_DECLINED"
        elif state.get("phase") == "abandoned":
            outcome = "ABANDONED"
        else:
            outcome = "FOLLOW_UP"
            
        # Calculate metrics
        client_messages = [m for m in messages if state["client_name"] in m["sender"]]
        wandero_messages = [m for m in messages if state["client_name"] not in m["sender"]]
        
        # Time analysis
        if messages:
            total_time = messages[-1]["timestamp"] - messages[0]["timestamp"]
            avg_response_time = total_time / len(messages) if len(messages) > 1 else timedelta(0)
        else:
            total_time = timedelta(0)
            avg_response_time = timedelta(0)
            
        summary = {
            "scenario": f"{persona_type} + {company_type}",
            "outcome": outcome,
            "metrics": {
                "total_emails": len(messages),
                "client_emails": len(client_messages),
                "wandero_emails": len(wandero_messages),
                "conversation_duration": str(total_time),
                "avg_response_time": str(avg_response_time),
                "final_interest_level": state.get("interest_level", 0),
                "discounts_offered": state.get("discounts_offered", 0),
                "proposals_made": len(state.get("proposals_made", []))
            },
            "quality": {
                "information_gathered": state.get("all_info_gathered", False),
                "concerns_addressed": len(state.get("client_concerns", [])) == 0,
                "natural_flow": True,
                "personality_match": True
            }
        }
        
        return summary
    
    def _save_conversation(self, persona_type: str, company_type: str,
                          state: ConversationState, summary: Dict):
        """Save conversation and summary"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"conversation_{persona_type}_{company_type}_{timestamp}.json"
        
        # Prepare data for JSON serialization
        messages_data = []
        for msg in state.get("messages", []):
            messages_data.append({
                "subject": msg["subject"],
                "body": msg["body"],
                "sender": msg["sender"],
                "timestamp": msg["timestamp"].isoformat(),
                "sentiment": msg.get("sentiment")
            })
        
        data = {
            "summary": summary,
            "messages": messages_data,
            "final_state": {
                "phase": state.get("phase"),
                "interest_level": state.get("interest_level"),
                "ready_to_book": state.get("ready_to_book"),
                "all_info_gathered": state.get("all_info_gathered")
            }
        }
        
        filepath = self.output_dir / filename
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
            
        print(f"\n💾 Conversation saved to: {filepath}")
    
    def run_simulation(self, scenarios: List[Tuple[str, str]]):
        """Run multiple scenarios"""
        print("\n" + "="*80)
        print("WANDERO CONVERSATION SIMULATION (LangGraph)")
        print("="*80)
        
        results = []
        
        for persona_type, company_type in scenarios:
            result = asyncio.run(self.run_conversation(persona_type, company_type))
            results.append(result)
            
            print(f"\n✅ Completed: {result['outcome']}")
            print("-"*60)
            
        self._generate_report(results)
    
    def _generate_report(self, results: List[Dict]):
        """Generate final report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_scenarios": len(results),
            "outcomes": {},
            "avg_metrics": {},
            "scenarios": results
        }
        
        # Count outcomes
        for result in results:
            outcome = result["outcome"]
            report["outcomes"][outcome] = report["outcomes"].get(outcome, 0) + 1
            
        # Calculate averages
        if results:
            report["avg_metrics"] = {
                "avg_emails": sum(r["metrics"]["total_emails"] for r in results) / len(results),
                "avg_interest": sum(r["metrics"]["final_interest_level"] for r in results) / len(results),
                "booking_rate": report["outcomes"].get("BOOKING_CONFIRMED", 0) / len(results)
            }
        
        # Save report
        report_path = self.output_dir / f"simulation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
            
        print(f"\n📊 SIMULATION COMPLETE")
        print(f"Total scenarios: {report['total_scenarios']}")
        for outcome, count in report["outcomes"].items():
            print(f"{outcome}: {count}")
        print(f"\nReport saved to: {report_path}")


def main():
    """Main entry point"""
    API_KEY = os.getenv("GOOGLE_API_KEY", "your-api-key-here")
    
    if API_KEY == "your-api-key-here":
        print("Please set GOOGLE_API_KEY environment variable")
        return
        
    orchestrator = ConversationOrchestrator(API_KEY)
    
    # Test scenarios
    scenarios = [
        ("budget_backpacker", "luxury_chile") # Should abondon.
    ]

    # ,      # Mismatch
    #     ("worried_parent", "family_adventures"),    # Good match
    #     ("adventure_couple", "chile_adventures"),   # Perfect match
    
    orchestrator.run_simulation(scenarios)


if __name__ == "__main__":
    main()