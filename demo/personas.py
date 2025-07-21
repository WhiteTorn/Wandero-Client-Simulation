"""Client personas for realistic simulation"""

PERSONAS = {
    "worried_parent": {
        "name": "Sarah Johnson",
        "type": "Family Vacation Planner",
        "traits": [
            "detail-oriented",
            "safety-conscious", 
            "budget-aware",
            "asks many questions"
        ],
        "family": {
            "adults": 2,
            "children": [
                {"age": 12, "name": "Emma"},
                {"age": 8, "name": "Jack"}
            ]
        },
        "communication_style": "polite but thorough",
        "concerns": [
            "child-friendly activities",
            "medical facilities nearby",
            "food allergies (Jack is allergic to nuts)",
            "safety in desert areas"
        ],
        "budget_range": "$4000-6000 total",
        "quirks": [
            "Often forgets to mention important details initially",
            "Sends follow-up emails with 'one more question'",
            "Mentions husband's preferences separately"
        ],
        "travel_dates": {
            "preferred": "July 15-22, 2024",
            "flexible": "Can shift by a week if needed"
        }
    },
    
    "spontaneous_couple": {
        "name": "Mike Chen",
        "type": "Adventure Seekers",
        "traits": ["flexible", "adventure-seeking", "tech-savvy"],
        "communication_style": "casual, uses emojis 😊",
        "budget_range": "$3000-4000 per person"
    }
}