import asyncio
import json
from datetime import datetime
from typing import List, Tuple, Dict, Optional
import os
from pathlib import Path

# Import Google Gemini
import google.generativeai as genai

from dotenv import load_dotenv

# Import our agents
from client_agent import (
    create_initial_client_state, 
    get_client_action, 
    generate_client_email
)
from wandero_agent import (
    create_initial_wandero_state, 
    get_wandero_action, 
    generate_wandero_email,
    parse_client_info
)
from personas import PERSONAS
from companies import COMPANIES

load_dotenv()

delay = 20

class EmailConversationOrchestrator:
    def __init__(self, api_key: str):
        """Initialize the orchestrator with Gemini API"""
        genai.configure(api_key=api_key)
        self.llm = genai.GenerativeModel('gemini-2.0-flash')
        
        # Create outputs directory
        self.output_dir = Path("outputs")
        self.output_dir.mkdir(exist_ok=True)
        
        # Email formatting settings
        self.email_width = 70
    
    def _get_llm_response(self, prompt: str) -> str:
        """Get response from Gemini LLM"""
        try:
            response = self.llm.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"LLM Error: {e}")
            return ""
    
    def _format_email_display(self, email_data: Dict, sender: str) -> str:
        """Format email for display"""
        divider = "=" * self.email_width
        return f"""
{divider}
From: {sender}
Subject: {email_data.get('subject', 'No Subject')}
{'-' * self.email_width}
{email_data.get('body', 'No content')}
{divider}
"""
    
    async def run_conversation(self, persona_type: str, company_type: str) -> Dict:
        """Run email conversation between persona and company"""
        print(f"\n{'='*80}")
        print(f"Starting Email Conversation: {persona_type} <-> {company_type}")
        print(f"{'='*80}\n")
        
        # Initialize states
        persona = PERSONAS.get(persona_type)
        company = COMPANIES.get(company_type)
        
        if not persona or not company:
            return {"error": "Invalid persona or company type"}
        
        client_state = create_initial_client_state(persona)
        wandero_state = create_initial_wandero_state(company)
        
        # Tracking
        email_thread = []
        turn_count = 0
        max_turns = 10  # More turns for email conversations
        
        # Start with Wandero introduction email
        print("\n📧 NEW EMAIL THREAD STARTED\n")
        
        wandero_intro = generate_wandero_email(
            wandero_state, 
            "greet_and_qualify", 
            self.llm
        )
        
        print(self._format_email_display(
            wandero_intro, 
            f"{wandero_state['agent_name']} <{wandero_state['company_name']}>"
        ))
        
        email_thread.append({
            "turn": 0,
            "sender": "wandero",
            "from": f"{wandero_state['agent_name']} <{wandero_state['company_name']}>",
            "subject": wandero_intro["subject"],
            "body": wandero_intro["body"],
            "timestamp": datetime.now().isoformat()
        })
        
        # Update client state with Wandero's introduction
        client_state["messages"].append({
            "role": "wandero",
            "content": wandero_intro["body"],
            "subject": wandero_intro["subject"]
        })
        client_state["last_email_subject"] = wandero_intro["subject"]
        
        # Main conversation loop
        while turn_count < max_turns:
            turn_count += 1
            
            # Client turn - they respond to Wandero
            await asyncio.sleep(delay)  # Simulate email delay
            
            # Get client action
            if turn_count == 1:
                client_action = "initial_inquiry"  # First response
            else:
                client_action = get_client_action(client_state, self.llm)
            
            # Generate client email
            client_email = generate_client_email(
                client_state,
                client_action,
                self.llm
            )

            await asyncio.sleep(delay)
            
            print(f"\n⏱️  Client composing reply...\n")
            print(self._format_email_display(
                client_email,
                f"{client_state['persona_name']} <{client_state['persona_name'].lower().replace(' ', '.')}@email.com>"
            ))
            
            email_thread.append({
                "turn": turn_count,
                "sender": "client",
                "from": f"{client_state['persona_name']}",
                "subject": client_email["subject"],
                "body": client_email["body"],
                "timestamp": datetime.now().isoformat()
            })
            
            # Parse client info for Wandero
            parse_client_info(wandero_state, client_email["body"])
            
            # Update Wandero state
            wandero_state["messages"].append({
                "role": "client",
                "content": client_email["body"],
                "subject": client_email["subject"]
            })
            wandero_state["last_email_subject"] = client_email["subject"]
            
            # Check if conversation should end
            if client_state["phase"] == "done":
                break
            
            # Wandero turn - they respond to client
            await asyncio.sleep(delay)
            
            # Get Wandero action
            wandero_action = get_wandero_action(wandero_state, self.llm)
            
            # Generate Wandero email
            await asyncio.sleep(delay)
            wandero_email = generate_wandero_email(
                wandero_state,
                wandero_action,
                self.llm
            )
            
            print(f"\n⏱️  Wandero composing reply...\n")
            print(self._format_email_display(
                wandero_email,
                f"{wandero_state['agent_name']} <{wandero_state['company_name']}>"
            ))
            
            email_thread.append({
                "turn": turn_count,
                "sender": "wandero",
                "from": f"{wandero_state['agent_name']} <{wandero_state['company_name']}>",
                "subject": wandero_email["subject"],
                "body": wandero_email["body"],
                "timestamp": datetime.now().isoformat()
            })
            
            # Update client state
            client_state["messages"].append({
                "role": "wandero",
                "content": wandero_email["body"],
                "subject": wandero_email["subject"]
            })
            client_state["last_email_subject"] = wandero_email["subject"]
            
            # Check end conditions
            if wandero_state["phase"] == "done":
                break
            
            # Natural conversation ending check
            if turn_count > 10 and client_state["interest_level"] < 0.4:
                # Likely to abandon
                client_state["abandonment_risk"] = 0.8
        
        # Generate summary
        summary = self._generate_summary(
            persona_type, company_type,
            client_state, wandero_state,
            email_thread
        )
        
        # Save email thread
        self._save_email_thread(
            persona_type, company_type,
            email_thread, summary
        )
        
        return summary
    
    def _generate_summary(self, persona_type: str, company_type: str,
                         client_state, wandero_state, 
                         email_thread: List[Dict]) -> Dict:
        """Generate conversation summary and analytics"""
        
        # Determine outcome
        if client_state["ready_to_book"]:
            outcome = "BOOKING_CONFIRMED"
        elif client_state["phase"] == "done" and client_state["interest_level"] < 0.5:
            outcome = "CLIENT_DECLINED"
        elif wandero_state["phase"] == "done" and client_state["interest_level"] > 0.5:
            outcome = "FOLLOW_UP_SCHEDULED"
        else:
            outcome = "CONVERSATION_ONGOING"
        
        # Analyze email patterns
        client_emails = [e for e in email_thread if e["sender"] == "client"]
        wandero_emails = [e for e in email_thread if e["sender"] == "wandero"]
        
        summary = {
            "scenario": f"{persona_type} + {company_type}",
            "timestamp": datetime.now().isoformat(),
            "outcome": outcome,
            "email_metrics": {
                "total_emails": len(email_thread),
                "client_emails": len(client_emails),
                "wandero_emails": len(wandero_emails),
                "avg_client_email_length": sum(len(e["body"]) for e in client_emails) // len(client_emails) if client_emails else 0,
                "avg_wandero_email_length": sum(len(e["body"]) for e in wandero_emails) // len(wandero_emails) if wandero_emails else 0,
            },
            "engagement_metrics": {
                "final_interest_level": client_state["interest_level"],
                "concerns_addressed": len(client_state["persona_data"].get("worries", [])) - len(client_state["concerns"]),
                "information_completeness": (5 - len(wandero_state["missing_info"])) / 5,
                "discounts_offered": wandero_state["discounts_offered"],
                "proposals_made": len(wandero_state["proposals_made"])
            },
            "conversation_quality": {
                "client_personality_consistency": self._check_personality_consistency(client_emails, client_state["persona_data"]),
                "natural_flow": True,
                "appropriate_outcome": True
            }
        }
        
        return summary
    
    def _check_personality_consistency(self, emails: List[Dict], persona_data: Dict) -> bool:
        """Check if email tone matches personality"""
        personality = persona_data.get("personality", "").lower()
        
        # Simple keyword analysis
        email_text = " ".join(e["body"].lower() for e in emails)
        
        if personality == "cautious":
            cautious_words = ["concern", "worried", "question", "clarify", "understand"]
            return any(word in email_text for word in cautious_words)
        elif personality == "spontaneous":
            spontaneous_words = ["excited", "love", "amazing", "can't wait", "perfect"]
            return any(word in email_text for word in spontaneous_words)
        elif personality == "budget-conscious":
            budget_words = ["price", "cost", "budget", "afford", "expensive", "deal"]
            return any(word in email_text for word in budget_words)
        
        return True
    
    def _save_email_thread(self, persona_type: str, company_type: str,
                          email_thread: List[Dict], summary: Dict):
        """Save email thread and summary"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"email_thread_{persona_type}_{company_type}_{timestamp}.json"
        filepath = self.output_dir / filename
        
        data = {
            "summary": summary,
            "email_thread": email_thread,
            "metadata": {
                "persona_type": persona_type,
                "company_type": company_type,
                "conversation_medium": "email",
                "llm_model": "gemini-2.0-flash-exp"
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Also save a readable version
        readable_filepath = self.output_dir / f"readable_{filename.replace('.json', '.txt')}"
        with open(readable_filepath, 'w') as f:
            f.write(f"Email Conversation: {persona_type} <-> {company_type}\n")
            f.write("="*80 + "\n\n")
            
            for email in email_thread:
                f.write(f"From: {email['from']}\n")
                f.write(f"Subject: {email['subject']}\n")
                f.write(f"Time: {email['timestamp']}\n")
                f.write("-"*80 + "\n")
                f.write(email['body'])
                f.write("\n\n" + "="*80 + "\n\n")
            
            f.write("\nCONVERSATION SUMMARY\n")
            f.write("-"*80 + "\n")
            f.write(f"Outcome: {summary['outcome']}\n")
            f.write(f"Total Emails: {summary['email_metrics']['total_emails']}\n")
            f.write(f"Client Interest: {summary['engagement_metrics']['final_interest_level']:.1%}\n")
            f.write(f"Information Gathered: {summary['engagement_metrics']['information_completeness']:.1%}\n")
        
        print(f"\n📁 Email thread saved to: {filepath}")
        print(f"📄 Readable version: {readable_filepath}")
    
    def run_simulation(self, test_scenarios: List[Tuple[str, str]]):
        """Run multiple test scenarios"""
        print("\n" + "="*80)
        print("WANDERO EMAIL SIMULATION SYSTEM")
        print("="*80)
        
        results = []
        
        for i, (persona_type, company_type) in enumerate(test_scenarios, 1):
            print(f"\n\n{'🚀 '*10}")
            print(f"SCENARIO {i}/{len(test_scenarios)}")
            print(f"{'🚀 '*10}")
            
            result = asyncio.run(self.run_conversation(persona_type, company_type))
            results.append(result)
            
            print(f"\n✅ Scenario completed: {result['outcome']}")
            print("-"*60)
        
        # Generate final report
        self._generate_final_report(results)
    
    def _generate_final_report(self, results: List[Dict]):
        """Generate final simulation report"""
        report = {
            "simulation_date": datetime.now().isoformat(),
            "total_scenarios": len(results),
            "outcomes": {
                "bookings": len([r for r in results if r["outcome"] == "BOOKING_CONFIRMED"]),
                "declines": len([r for r in results if r["outcome"] == "CLIENT_DECLINED"]),
                "follow_ups": len([r for r in results if r["outcome"] == "FOLLOW_UP_SCHEDULED"]),
                "ongoing": len([r for r in results if r["outcome"] == "CONVERSATION_ONGOING"])
            },
            "average_metrics": {
                "avg_emails_per_conversation": sum(r["email_metrics"]["total_emails"] for r in results) / len(results),
                "avg_final_interest": sum(r["engagement_metrics"]["final_interest_level"] for r in results) / len(results),
                "avg_info_completeness": sum(r["engagement_metrics"]["information_completeness"] for r in results) / len(results),
            },
            "scenarios": results
        }
        
        report_path = self.output_dir / f"simulation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n{'='*80}")
        print("📊 SIMULATION COMPLETE")
        print(f"{'='*80}")
        print(f"Total scenarios: {report['total_scenarios']}")
        print(f"✅ Successful bookings: {report['outcomes']['bookings']}")
        print(f"❌ Client declines: {report['outcomes']['declines']}")
        print(f"📅 Follow-ups scheduled: {report['outcomes']['follow_ups']}")
        print(f"⏳ Ongoing conversations: {report['outcomes']['ongoing']}")
        print(f"\n📈 Average emails per conversation: {report['average_metrics']['avg_emails_per_conversation']:.1f}")
        print(f"💡 Average final interest level: {report['average_metrics']['avg_final_interest']:.1%}")
        print(f"\n📁 Full report saved to: {report_path}")


def main():
    """Main entry point"""
    # Set your Gemini API key
    API_KEY = os.getenv("GOOGLE_API_KEY", "your-api-key-here")
    
    if API_KEY == "your-api-key-here":
        print("Please set your GEMINI_API_KEY environment variable")
        return
    
    # Initialize orchestrator
    orchestrator = EmailConversationOrchestrator(API_KEY)
    
    # Define test scenarios
    test_scenarios = [
        
        ("budget_backpacker", "luxury_chile"),      # Bad match
             # Standard match
    ]
    
    # Run simulation
    orchestrator.run_simulation(test_scenarios)

    # ("adventure_couple", "chile_adventures"),   # Perfect match
    #     ("solo_traveler", "patagonia_tours"),  
    # ("worried_parent", "family_adventures"),    # Good match


if __name__ == "__main__":
    main()