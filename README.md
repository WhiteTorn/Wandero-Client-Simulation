# Wandero Client Simulation

Gemini Based Client Simulation for the Wandero's Agent.

Current Version is interactive demo which requires company email to start communication and company information asked in the CLI.

## Overview

This sistem simulates realistic client behavior to test Wandero's travel planning agents.
it creates authentic email conversations where AI personas:

- Send initial travel inquiries
- Respond naturally
- Exhibit realistic behaviors
- Track conversation progress
- Provide analytics

## System Architecture

Client Agent | Gmail Client | Wandero
(gemini) | (OAuth 2.0) | (Agent, in current case I was sending mails)

also I provide the Demo Mode which supports realistic timing for authentic demonstration, but it requires too much time to test.

## Installation

### Clone Repo
```
git clone https://github.com/your-username/wandero-client-simulation
cd wandero-client-simulation
```

### Install Dependencies
```
pip install -r requirements.txt
```

### Create Environment file
```
.env 

GOOGLE_API_KEY=your_google_ai_api_key_here
```

## USAGE

```bash
python main.py
```

### Interactive Setup Process
1. **Select Persona**: Choose from 6 available client types
2. **Choose Mode**: TEST (immediate) or DEMO (realistic timing)  
3. **Enter Wandero Email**: Target Wandero agent email address
4. **Company Information**: Travel company details for context

### Example Interaction flows

**🎭 Adventure Couple Success Story**  
[**→ View Complete Conversation**](conversation_states/adventure.md)  
Fast-paced, enthusiastic booking that completed in 25 minutes with a $8,500 package

**💼 Business Solo Professional Journey**  
[**→ View Complete Conversation**](conversation_states/business.md)  
Professional, detailed inquiry process leading to a scheduled consultation call

Both demonstrate authentic persona behaviors, realistic email timing, and natural conversation progression that would help Wandero test their agent responses effectively.


## Conclusion

Project was very interesting and I might create something similar for other systems too.