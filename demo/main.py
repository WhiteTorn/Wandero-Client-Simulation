"""Main demo runner with proper LangGraph integration"""

import os
from datetime import datetime
from dotenv import load_dotenv

from client_graph import create_client_graph, create_initial_state
from wandero_bot import WanderoBot

load_dotenv()

def print_email(sender: str, content: str, delay_note: str = ""):
    """Pretty print email"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"\n{'='*60}")
    print(f"📧 From: {sender}")
    print(f"🕐 Time: {timestamp} {delay_note}")
    print(f"{'='*60}")
    print(content)
    print(f"{'='*60}\n")

def print_state_debug(state: dict, round_num: int):
    """Print detailed state information for debugging"""
    print(f"🔍 DEBUG STATE (Round {round_num}):")
    print(f"   📍 Current Phase: {state.get('phase', 'unknown')}")
    print(f"   🗣️ Persona: {state.get('persona_name', 'unknown')} ({state.get('persona_type', 'unknown')})")
    print(f"   💬 Total Messages: {len(state.get('messages', []))}")
    print(f"   📝 Provided Info: {state.get('provided_info', {})}")
    print(f"   ✅ Mentioned Details: {state.get('mentioned_details', [])}")
    print(f"   🔄 Turn Count: {state.get('turn', 0)}")
    
    # Show last few messages
    messages = state.get('messages', [])
    if messages:
        print(f"   📜 Recent Messages:")
        for i, msg in enumerate(messages[-3:]):  # Last 3 messages
            role_emoji = "👤" if msg['role'] == 'client' else "🏢" if msg['role'] == 'wandero' else "⚙️"
            print(f"      {role_emoji} {msg['role']}: {msg['content'][:100]}{'...' if len(msg['content']) > 100 else ''}")
    print()

def run_conversation_demo():
    """Run the complete demo with proper LangGraph flow"""
    
    print("\n🚀 WANDERO CLIENT SIMULATION - LANGGRAPH DEMO")
    print("=" * 60)
    
    print("🔧 INITIALIZATION PHASE")
    print("-" * 30)
    
    # Initialize components
    persona_type = "worried_parent"
    print(f"📋 Selected persona type: {persona_type}")
    
    print("🏗️ Creating client graph...")
    try:
        client_graph = create_client_graph(persona_type)
        print("✅ Client graph created successfully")
    except Exception as e:
        print(f"❌ Error creating client graph: {e}")
        return
        
    print("🤖 Initializing Wandero bot...")
    try:
        wandero = WanderoBot()
        print("✅ Wandero bot initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing Wandero bot: {e}")
        return
    
    # Create initial state
    print("🌱 Creating initial state...")
    try:
        initial_state = create_initial_state(persona_type)
        print("✅ Initial state created successfully")
        print_state_debug(initial_state, 0)
    except Exception as e:
        print(f"❌ Error creating initial state: {e}")
        return
    
    # Configuration for the graph run
    config = {"configurable": {"thread_id": "demo_conversation_1"}}
    print(f"⚙️ Graph configuration: {config}")
    
    print(f"\n👤 Client: {initial_state['persona_name']} ({initial_state['persona_type']})")
    print("🏢 Company: Chile Adventures Ltd.\n")
    
    # Start the conversation
    print("🚀 CONVERSATION PHASE")
    print("-" * 30)
    print("Starting automated conversation...\n")
    
    # Run the graph with initial state
    current_state = initial_state
    max_rounds = 8
    
    for i in range(max_rounds):
        print(f"\n{'='*20} ROUND {i+1}/{max_rounds} {'='*20}")
        
        print(f"🔄 Invoking client graph (Round {i+1})...")
        print(f"📊 Pre-invocation state check:")
        print_state_debug(current_state, i+1)
        
        # Invoke the graph to get next action
        try:
            print("⚡ Executing graph.invoke()...")
            result = client_graph.invoke(current_state, config)
            print("✅ Graph invocation successful")
            
            # Update current state
            current_state = result
            print("🔄 State updated with graph result")
            
        except Exception as e:
            print(f"❌ Error during graph invocation: {e}")
            print(f"🔍 Current state at error: {current_state}")
            break
        
        print(f"📊 Post-invocation state check:")
        print_state_debug(current_state, i+1)
        
        # Get the latest client message
        print("🔍 Searching for new client messages...")
        client_messages = [m for m in result["messages"] if m["role"] == "client"]
        print(f"📈 Found {len(client_messages)} total client messages")
        
        if client_messages:
            latest_client_msg = client_messages[-1]["content"]
            print(f"📝 Latest client message preview: {latest_client_msg[:100]}...")
            
            # Check for system messages (delays)
            print("🔍 Checking for system messages (delays)...")
            delay_note = ""
            for j in range(len(result["messages"]) - 1, -1, -1):
                if result["messages"][j]["role"] == "system":
                    delay_note = result["messages"][j]["content"]
                    print(f"⏰ Found delay note: {delay_note}")
                    break
            
            if not delay_note:
                print("ℹ️ No delay note found")
            
            print("📧 Displaying client email...")
            print_email(
                f"{result['persona_name']} (Client)",
                latest_client_msg,
                delay_note
            )
            
            # Wandero responds
            print("🤖 Generating Wandero response...")
            try:
                wandero_response = wandero.process_message(latest_client_msg, i)
                print(f"✅ Wandero response generated: {wandero_response[:100]}...")
                
                print("📧 Displaying Wandero email...")
                print_email("Maria Rodriguez (Wandero)", wandero_response)
                
            except Exception as e:
                print(f"❌ Error generating Wandero response: {e}")
                wandero_response = "Thank you for your message. We'll get back to you soon."
                print("🔄 Using fallback response")
            
            # Add Wandero's response to state
            print("💾 Adding Wandero response to conversation state...")
            current_state["messages"].append({
                "role": "wandero",
                "content": wandero_response,
                "turn": i
            })
            print("✅ Wandero response added to state")
            
        else:
            print("ℹ️ No new client messages found in this round")
        
        # Check if conversation ended
        current_phase = current_state.get("phase", "unknown")
        print(f"🏁 Checking end condition - Current phase: {current_phase}")
        
        if current_phase == "conversation_ended":
            print("🎯 Conversation ended condition met - breaking loop")
            break
        elif i == max_rounds - 1:
            print("⏰ Maximum rounds reached - ending conversation")
        else:
            print("➡️ Continuing to next round...")
    
    # Summary
    print("\n" + "="*60)
    print("📊 CONVERSATION SUMMARY")
    print("="*60)
    
    total_client_msgs = len([m for m in current_state['messages'] if m['role'] == 'client'])
    total_wandero_msgs = len([m for m in current_state['messages'] if m['role'] == 'wandero'])
    total_system_msgs = len([m for m in current_state['messages'] if m['role'] == 'system'])
    
    print(f"📈 Total client messages: {total_client_msgs}")
    print(f"🏢 Total Wandero messages: {total_wandero_msgs}")
    print(f"⚙️ Total system messages: {total_system_msgs}")
    print(f"💬 Total conversation messages: {len(current_state['messages'])}")
    
    provided_info = current_state.get('provided_info', {})
    provided_items = [k for k, v in provided_info.items() if v]
    print(f"📝 Information provided: {', '.join(provided_items) if provided_items else 'None'}")
    print(f"📍 Final phase: {current_state.get('phase', 'unknown')}")
    print(f"🏷️ Final mentioned details: {current_state.get('mentioned_details', [])}")
    
    print(f"\n🎯 Final State Summary:")
    print_state_debug(current_state, "Final")
    
    print("\n✅ Demo completed successfully!")

if __name__ == "__main__":
    print("🚀 Starting Wandero Client Simulation Demo...")
    print(f"⏰ Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        run_conversation_demo()
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        print("💥 Demo failed to complete")
    
    print(f"⏰ End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("👋 Demo finished!")