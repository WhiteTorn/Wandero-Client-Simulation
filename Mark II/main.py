import asyncio
import json
from datetime import datetime
from typing import List, Tuple, Dict
import os
from pathlib import Path
from dotenv import load_dotenv

# Import Google Gemini
import google.generativeai as genai

# Import our agents
from client_agent import create_initial_client_state, get_client_action, execute_client_node
from wandero_agent import create_initial_wandero_state, get_wandero_action, execute_wandero_node
from personas import PERSONAS
from companies import COMPANIES
import time

load_dotenv()

class ConversationOrchestrator:
    def __init__(self, api_key: str):
        """Initialize the orchestrator with Gemini API"""
        genai.configure(api_key=api_key)
        self.llm = genai.GenerativeModel('gemini-2.0-flash')
        
        # Create outputs directory
        self.output_dir = Path("outputs")
        self.output_dir.mkdir(exist_ok=True)
    
    def _get_llm_response(self, prompt: str) -> str:
        """Get response from Gemini LLM"""
        try:
            response = self.llm.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"LLM Error: {e}")
            return ""
    
    async def run_conversation(self, persona_type: str, company_type: str) -> Dict:
        """Run a single conversation between persona and company"""
        print(f"\n{'='*60}")
        print(f"Starting conversation: {persona_type} <-> {company_type}")
        print(f"{'='*60}\n")
        
        # Initialize states
        persona = PERSONAS.get(persona_type)
        company = COMPANIES.get(company_type)
        
        if not persona or not company:
            return {"error": "Invalid persona or company type"}
        
        client_state = create_initial_client_state(persona)
        wandero_state = create_initial_wandero_state(company)
        
        # Track conversation
        conversation_log = []
        turn_count = 0
        max_turns = 15
        
        # First turn - client initiates
        client_action = "initial_inquiry"
        client_response = execute_client_node(client_action, client_state)
        
        print(f"Client ({persona['name']}): {client_response}")
        conversation_log.append({
            "turn": turn_count,
            "speaker": "client",
            "action": client_action,
            "message": client_response
        })
        
        # Update Wandero's state with client message
        wandero_state["messages"].append({"role": "client", "content": client_response})
        
        # Main conversation loop
        while turn_count < max_turns:
            time.sleep(15)
            turn_count += 1
            
            # Wandero turn
            wandero_action = self._get_llm_response(
                self._build_wandero_prompt(wandero_state)
            )
            if not wandero_action:
                wandero_action = get_wandero_action(wandero_state, self)
            
            wandero_response = execute_wandero_node(wandero_action, wandero_state)
            
            print(f"\nWandero ({company['name']}): {wandero_response}")
            conversation_log.append({
                "turn": turn_count,
                "speaker": "wandero",
                "action": wandero_action,
                "message": wandero_response
            })
            
            # Update client's state
            client_state["messages"].append({"role": "wandero", "content": wandero_response})
            
            # Check if conversation should end
            if wandero_state["phase"] == "done" or client_state["phase"] == "done":
                break
            
            # Client turn
            client_action = self._get_llm_response(
                self._build_client_prompt(client_state)
            )
            if not client_action:
                client_action = get_client_action(client_state, self)
            
            client_response = execute_client_node(client_action, client_state)
            
            print(f"\nClient ({persona['name']}): {client_response}")
            conversation_log.append({
                "turn": turn_count,
                "speaker": "client", 
                "action": client_action,
                "message": client_response
            })
            
            # Update Wandero's state
            wandero_state["messages"].append({"role": "client", "content": client_response})
            
            # Check end conditions
            if client_action in ["make_decision", "abandon"]:
                # Give Wandero one last response
                if client_state["ready_to_book"]:
                    wandero_action = "close_deal"
                else:
                    wandero_action = "follow_up" if client_state["interest_level"] > 0.5 else "accept_loss"
                
                wandero_response = execute_wandero_node(wandero_action, wandero_state)
                print(f"\nWandero ({company['name']}): {wandero_response}")
                conversation_log.append({
                    "turn": turn_count + 1,
                    "speaker": "wandero",
                    "action": wandero_action,
                    "message": wandero_response
                })
                break
        
        # Generate summary
        summary = self._generate_summary(
            persona_type, company_type, 
            client_state, wandero_state, 
            conversation_log
        )
        
        # Save conversation
        self._save_conversation(
            persona_type, company_type,
            conversation_log, summary
        )
        
        return summary
    
    def _build_client_prompt(self, state) -> str:
        """Build prompt for client action selection"""
        last_message = state["messages"][-1]["content"] if state["messages"] else "None"
        
        return f"""You are deciding the next action for a travel client.

Client: {state['persona_name']}
Personality: {state['persona_data'].get('personality', 'standard')}
Phase: {state['phase']}
Interest: {state['interest_level']:.1f}/1.0
Concerns left: {len(state['concerns'])}

Last agent message: {last_message}

Available actions:
- provide_details (if info needed)
- express_interest (if liking proposal)
- raise_concern (if worried)
- negotiate (if interested but want better deal)
- make_decision (if ready to decide)
- send_correction (if forgot something)
- abandon (if not interested)

What should the client do? Return ONLY the action name."""
    
    def _build_wandero_prompt(self, state) -> str:
        """Build prompt for Wandero action selection"""
        last_message = ""
        for msg in reversed(state["messages"]):
            if msg["role"] == "client":
                last_message = msg["content"]
                break
        
        return f"""You are deciding the next action for a travel agent.

Company: {state['company_name']} ({state['company_data'].get('type', 'standard')})
Phase: {state['phase']}
Info needed: {len(state['missing_info'])}
Proposals made: {len(state['proposals_made'])}

Last client message: {last_message}

Available actions:
- gather_details (if missing key info)
- present_proposal (if have enough info)
- handle_objection (if client has concerns)
- offer_incentive (if client negotiating)
- close_deal (if client ready)
- follow_up (if client unsure)
- accept_loss (if client not interested)

What should the agent do? Return ONLY the action name."""
    
    def _generate_summary(self, persona_type: str, company_type: str,
                         client_state, wandero_state, 
                         conversation_log: List[Dict]) -> Dict:
        """Generate conversation summary and analytics"""
        
        # Determine outcome
        if client_state["ready_to_book"]:
            outcome = "BOOKING_CONFIRMED"
        elif client_state["phase"] == "done" and client_state["interest_level"] < 0.5:
            outcome = "CLIENT_DECLINED"
        elif wandero_state["phase"] == "done":
            outcome = "FOLLOW_UP_SCHEDULED"
        else:
            outcome = "INCOMPLETE"
        
        summary = {
            "scenario": f"{persona_type} + {company_type}",
            "timestamp": datetime.now().isoformat(),
            "outcome": outcome,
            "metrics": {
                "total_turns": len(conversation_log),
                "client_messages": len([log for log in conversation_log if log["speaker"] == "client"]),
                "wandero_messages": len([log for log in conversation_log if log["speaker"] == "wandero"]),
                "final_interest_level": client_state["interest_level"],
                "final_abandonment_risk": client_state["abandonment_risk"],
                "discounts_offered": wandero_state["discounts_offered"],
                "proposals_made": len(wandero_state["proposals_made"])
            },
            "client_journey": {
                "concerns_raised": len(client_state["persona_data"].get("worries", [])) - len(client_state["concerns"]),
                "information_shared": sum(client_state["shared_info"].values()),
                "corrections_made": len(client_state["important_points"])
            },
            "conversation_quality": {
                "natural_flow": True,  # Could be enhanced with more analysis
                "personality_consistency": True,
                "realistic_outcome": True
            }
        }
        
        return summary
    
    def _save_conversation(self, persona_type: str, company_type: str,
                          conversation_log: List[Dict], summary: Dict):
        """Save conversation and summary to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{persona_type}_{company_type}_{timestamp}.json"
        filepath = self.output_dir / filename
        
        data = {
            "summary": summary,
            "conversation": conversation_log
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"\nConversation saved to: {filepath}")
    
    def run_simulation(self, test_scenarios: List[Tuple[str, str]]):
        """Run multiple test scenarios and generate report"""
        print("\n" + "="*60)
        print("WANDERO TRAVEL AGENCY SIMULATION")
        print("="*60)
        
        results = []
        
        for persona_type, company_type in test_scenarios:
            result = asyncio.run(self.run_conversation(persona_type, company_type))
            results.append(result)
            print(f"\nScenario completed: {result['outcome']}")
            print("-"*40)
        
        # Generate final report
        self._generate_report(results)
    
    def _generate_report(self, results: List[Dict]):
        """Generate final simulation report"""
        report = {
            "simulation_date": datetime.now().isoformat(),
            "total_scenarios": len(results),
            "outcomes": {
                "bookings": len([r for r in results if r["outcome"] == "BOOKING_CONFIRMED"]),
                "declines": len([r for r in results if r["outcome"] == "CLIENT_DECLINED"]),
                "follow_ups": len([r for r in results if r["outcome"] == "FOLLOW_UP_SCHEDULED"])
            },
            "scenarios": results
        }
        
        report_path = self.output_dir / f"simulation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n{'='*60}")
        print("SIMULATION COMPLETE")
        print(f"{'='*60}")
        print(f"Total scenarios: {report['total_scenarios']}")
        print(f"Successful bookings: {report['outcomes']['bookings']}")
        print(f"Client declines: {report['outcomes']['declines']}")
        print(f"Follow-ups scheduled: {report['outcomes']['follow_ups']}")
        print(f"\nFull report saved to: {report_path}")


def main():
    """Main entry point"""
    # You'll need to set your Gemini API key
    API_KEY = os.getenv("GOOGLE_API_KEY", "your-api-key-here")
    
    if API_KEY == "your-api-key-here":
        print("Please set your GEMINI_API_KEY environment variable")
        return
    
    # Initialize orchestrator
    orchestrator = ConversationOrchestrator(API_KEY)
    
    # Define test scenarios
    test_scenarios = [
        ("worried_parent", "family_adventures"),  # Good match
        ("budget_backpacker", "luxury_chile"),    # Bad match
        ("adventure_couple", "chile_adventures"),  # Perfect match
        ("solo_traveler", "patagonia_tours"),      # Negotiation scenario
    ]
    
    # Run simulation
    orchestrator.run_simulation(test_scenarios)


if __name__ == "__main__":
    main()