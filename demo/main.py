"""Main demo runner"""

import time
from datetime import datetime
from client_simulator import create_client_graph, initialize_client_state
from mock_wandero import MockWandero

def print_email(sender: str, recipient: str, content: str, timestamp: str = None):
    """Pretty print an email"""
    if not timestamp:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"\n{'='*60}")
    print(f"From: {sender}")
    print(f"To: {recipient}")
    print(f"Time: {timestamp}")
    print(f"{'='*60}")
    print(content)
    print(f"{'='*60}\n")

def simulate_conversation():
    """Run the complete conversation simulation"""
    print("\n🚀 WANDERO CLIENT SIMULATION DEMO")
    print("Simulating realistic client-agency email exchange...\n")
    
    # Initialize systems
    client_graph = create_client_graph("worried_parent")
    client_state = initialize_client_state("worried_parent")
    wandero = MockWandero()
    
    # Get persona info for display
    persona = client_state["persona"]
    company = wandero.company
    
    print(f"Client Persona: {persona['name']} - {persona['type']}")
    print(f"Company: {company['name']} ({company['country']})")
    print(f"\nStarting conversation...\n")
    
    # Start with client inquiry - ADD ERROR HANDLING
    try:
        print(f"🔍 DEBUG: Initial state phase: {client_state['current_phase']}")
        print(f"🔍 DEBUG: Conversation count: {client_state['conversation_count']}")
        
        client_state = client_graph.invoke(client_state, {"recursion_limit": 50})
        
        print(f"🔍 DEBUG: After invoke - phase: {client_state['current_phase']}")
        print(f"🔍 DEBUG: Message count: {len(client_state['messages'])}")
        
    except Exception as e:
        print(f"❌ ERROR in client graph execution: {e}")
        print(f"🔍 DEBUG: Final state - phase: {client_state['current_phase']}")
        print(f"🔍 DEBUG: Messages: {len(client_state.get('messages', []))}")
        return
    
    # Extract the last client message
    client_message = client_state["messages"][-1]["content"]
    print_email(
        f"{persona['name']} <{persona['name'].lower().replace(' ', '.')}@email.com>",
        company['email'],
        client_message
    )
    
    # Simulate email delay - INCREASED
    print("⏰ Waiting for response... (simulating email delay)")
    time.sleep(5)  # Increased from 2 to 5 seconds

    print("📨 Wandero processing initial inquiry...")
    wandero_response = wandero.process_email(client_message, client_state)
    print_email(
        f"Maria Rodriguez <maria@{company['email']}>",
        f"{persona['name'].lower().replace(' ', '.')}@email.com",
        wandero_response
    )

    client_state["messages"].append({"role": "wandero", "content": wandero_response})

    
    # Rest of function with increased delays between each step...
    # Continue conversation for a few rounds
    max_rounds = 4
    for round in range(max_rounds):
        # Client analyzes and responds - INCREASED DELAY
        print(f"\n📧 Client preparing response (Round {round + 1}/{max_rounds})...")
        time.sleep(3)  # Increased from 1 to 3 seconds
        
        # Add delay before each major operation
        print("⏰ Processing response...")
        time.sleep(2)
        
        # Determine next action
        if "provide" in wandero_response.lower() and round == 0:
            # Provide details
            client_state = client_graph.invoke(client_state)
            client_message = client_state["messages"][-1]["content"]
            
            print_email(
                f"{persona['name']} <{persona['name'].lower().replace(' ', '.')}@email.com>",
                company['email'],
                client_message
            )
            
            # Maybe send a correction
            if round == 0 and len([m for m in client_state["messages"] if "forgot" in m.get("content", "").lower()]) == 0:
                print("\n💭 Client realizes they forgot something...")
                time.sleep(3)
                
                # Send correction
                client_state["current_phase"] = "details_provided"
                client_state["pending_corrections"] = ["children_ages"]
                
                # Import the send_correction function
                from client_simulator import send_correction
                client_state = send_correction(client_state)
                
                # Get the correction message
                correction_message = None
                for msg in reversed(client_state["messages"]):
                    if msg["role"] == "client":
                        correction_message = msg["content"]
                        break
                
                if correction_message:
                    print_email(
                        f"{persona['name']} <{persona['name'].lower().replace(' ', '.')}@email.com>",
                        company['email'],
                        correction_message,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " (5 minutes later)"
                    )
        
        # Wandero responds
        time.sleep(2)
        wandero_response = wandero.process_email(client_message, client_state)
        print_email(
            f"Maria Rodriguez <maria@{company['email']}>",
            f"{persona['name'].lower().replace(' ', '.')}@email.com",
            wandero_response
        )
        
        # Check if we have a proposal
        if "itinerary" in wandero_response.lower() and "cost" in wandero_response.lower():
            print("\n✅ Proposal received! Client is reviewing...")
            time.sleep(2)
            
            # Client confirms
            confirmation = """This looks absolutely perfect! The itinerary is exactly 
what we were hoping for, and the family suites sound great.

I'm ready to proceed with the booking. Please send the invoice 
and let me know the next steps.

Can't wait for our Chilean adventure!

Best regards,
Sarah"""
            
            print_email(
                f"{persona['name']} <{persona['name'].lower().replace(' ', '.')}@email.com>",
                company['email'],
                confirmation
            )
            
            # Final Wandero response
            time.sleep(1)
            final_response = wandero.process_email(confirmation, client_state)
            print_email(
                f"Maria Rodriguez <maria@{company['email']}>",
                f"{persona['name'].lower().replace(' ', '.')}@email.com",
                final_response
            )
            
            break
    
    print("\n✨ CONVERSATION COMPLETED!")
    print(f"Total exchanges: {len([m for m in client_state['messages'] if m['role'] == 'client'])}")
    print("\nKey demonstrated behaviors:")
    print("- Natural initial inquiry")
    print("- Forgetting important details")
    print("- Sending correction emails")
    print("- Realistic response delays")
    print("- Conversational tone throughout")

if __name__ == "__main__":
    simulate_conversation()