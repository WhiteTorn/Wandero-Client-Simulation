#!/usr/bin/env python3
"""
Interactive Client Simulation Agent for Wandero Testing

This agent simulates realistic client personas that communicate with Wandero 
via Gmail in real-time. Perfect for testing Wandero's response quality and timing.
"""

import asyncio
import os
import logging
import sys
from datetime import datetime
from dotenv import load_dotenv

from interactive_client_agent import InteractiveClientAgent
from personas import PERSONAS

# Load environment variables
load_dotenv()

def setup_logging():
    """Setup comprehensive logging for the demo"""
    # Create logs directory
    os.makedirs("logs", exist_ok=True)
    
    # Setup file logging
    log_filename = f"logs/client_simulation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # Configure logging with UTF-8 encoding for file, ASCII-safe for console
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    console_handler = logging.StreamHandler(sys.stdout)
    
    # Set formatters
    formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s', datefmt='%H:%M:%S')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, console_handler]
    )
    
    # Reduce noise from google api client
    logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)
    logging.getLogger('google.auth.transport.requests').setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info(f"[LOG] Logging to: {log_filename}")
    return logger

def print_banner():
    """Print application banner"""
    print("""
================================================================================
                    WANDERO CLIENT SIMULATION AGENT                        
                         Interactive Gmail Testing System                     
================================================================================
    """)

def print_personas():
    """Display available personas"""
    print("\n[PERSONAS] AVAILABLE CLIENT PERSONAS:\n")
    
    for persona_key, persona_data in PERSONAS.items():
        print(f"   * {persona_key}")
        print(f"      Name: {persona_data['name']}")
        print(f"      Type: {persona_data.get('personality', 'standard')}")
        print(f"      Budget: ${persona_data.get('budget', {}).get('min', 'unknown')}-${persona_data.get('budget', {}).get('max', 'unknown')}")
        print(f"      Group: {persona_data.get('travel_group', 'unknown')}")
        print(f"      Style: {persona_data.get('decision_style', 'unknown')}")
        print()

def get_user_input():
    """Get simulation parameters from user"""
    print("[SETUP] SIMULATION SETUP\n")
    
    # Show available personas
    print_personas()
    
    # Get persona selection
    while True:
        persona_type = input("Select persona type: ").strip()
        if persona_type in PERSONAS:
            break
        print(f"[ERROR] Invalid persona type. Choose from: {', '.join(PERSONAS.keys())}")
    
    # Get mode selection
    print("\n[MODE] Choose response timing mode:")
    print("  1. TEST MODE - Immediate responses (for fast testing)")
    print("  2. DEMO MODE - Realistic timing based on persona (for demonstrations)")
    
    while True:
        mode_choice = input("Select mode (1 or 2): ").strip()
        if mode_choice == "1":
            test_mode = True
            print("[MODE] TEST MODE selected - Agent will respond immediately")
            break
        elif mode_choice == "2":
            test_mode = False  
            print("[MODE] DEMO MODE selected - Agent will use realistic timing")
            break
        else:
            print("[ERROR] Please enter 1 or 2")
    
    # Get Wandero email
    while True:
        wandero_email = input("\nEnter Wandero agent email address: ").strip()
        if '@' in wandero_email and '.' in wandero_email:
            break
        print("[ERROR] Please enter a valid email address")
    
    # Get company information
    print("\n[INPUT] Enter company information:")
    company_name = input("Company name: ").strip() or "Travel Agency"
    company_country = input("Primary destination country: ").strip() or "Chile"
    
    specialties_input = input("Company specialties (comma-separated): ").strip()
    if specialties_input:
        specialties = [s.strip() for s in specialties_input.split(',')]
    else:
        specialties = ["adventure tours", "cultural experiences"]
    
    company_info = {
        "name": company_name,
        "country": company_country,
        "specialties": specialties
    }
    
    return persona_type, wandero_email, company_info, test_mode

def check_environment():
    """Check required environment variables and files"""
    logger = logging.getLogger(__name__)
    
    # Check Google API key
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        logger.error("[ERROR] GOOGLE_API_KEY not found in environment variables")
        logger.info("   Please add GOOGLE_API_KEY to your .env file")
        return False
    
    # Check Gmail credentials file
    credentials_file = "credentials.json"
    if not os.path.exists(credentials_file):
        logger.error(f"[ERROR] Gmail credentials file '{credentials_file}' not found")
        logger.info("   Please download OAuth 2.0 credentials from Google Cloud Console")
        logger.info("   and save as 'credentials.json' in the project root")
        return False
    
    logger.info("[SUCCESS] Environment check passed")
    return True

async def run_simulation():
    """Run the interactive client simulation"""
    logger = logging.getLogger(__name__)
    
    try:
        # Get user input (now includes test_mode)
        persona_type, wandero_email, company_info, test_mode = get_user_input()
        
        # Get API key
        google_api_key = os.getenv("GOOGLE_API_KEY")
        
        # Display simulation info
        mode_text = "TEST MODE (immediate)" if test_mode else "DEMO MODE (realistic timing)"
        print(f"\n[START] STARTING SIMULATION - {mode_text}")
        print(f"   Persona: {PERSONAS[persona_type]['name']} ({persona_type})")
        print(f"   Wandero: {wandero_email}")
        print(f"   Company: {company_info['name']} ({company_info['country']})")
        print(f"   Specialties: {', '.join(company_info['specialties'])}")
        print()
        
        # Create and initialize agent
        logger.info("[AGENT] Initializing Interactive Client Agent...")
        agent = InteractiveClientAgent(
            persona_type=persona_type,
            wandero_email=wandero_email,
            company_info=company_info,
            google_api_key=google_api_key,
            gmail_credentials_file="credentials.json",
            test_mode=test_mode
        )
        
        # Start conversation
        logger.info("[START] Starting conversation...")
        success = await agent.start_conversation()
        
        if not success:
            logger.error("[ERROR] Failed to start conversation")
            return
        
        # Run conversation loop
        logger.info("[MONITOR] Starting conversation monitoring loop...")
        await agent.run_conversation_loop()
        
        # Final report when conversation ends
        state = agent.state_manager.get_state()
        final_outcome = agent.state_manager.get_final_outcome()
        
        print(f"\n{'='*60}")
        print(f"CONVERSATION COMPLETED")
        print(f"{'='*60}")
        print(f"Final Phase: {state.get('phase', 'unknown')}")
        print(f"Final Outcome: {final_outcome or 'ongoing'}")
        print(f"Interest Level: {state.get('interest_level', 0.5):.2f}/1.0")
        print(f"Total Messages: {len(state.get('messages', []))}")
        print(f"Duration: {datetime.now() - state.get('conversation_start', datetime.now())}")
        
        if final_outcome == "booked":
            print(f"🎉 SUCCESS: Client booked the trip!")
        elif final_outcome == "abandoned":
            print(f"❌ ABANDONED: Client declined to book")
        else:
            print(f"⏱️  ONGOING: Conversation still in progress")
        
    except KeyboardInterrupt:
        logger.info("\n[EXIT] Simulation stopped by user")
    except Exception as e:
        logger.error(f"[ERROR] Simulation error: {str(e)}")
        raise

def main():
    """Main entry point"""
    # Setup logging
    logger = setup_logging()
    
    # Print banner
    print_banner()
    
    # Check environment
    if not check_environment():
        print("\n[ERROR] Environment check failed. Please fix the issues above and try again.")
        return
    
    # Run simulation
    try:
        asyncio.run(run_simulation())
    except KeyboardInterrupt:
        print("\n[EXIT] Goodbye!")
    except Exception as e:
        logger.error(f"[FATAL] Fatal error: {str(e)}")
        print(f"\n[FATAL] Fatal error: {str(e)}")
        print("Check the log file for more details.")

if __name__ == "__main__":
    main()