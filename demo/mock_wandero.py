"""Mock Wandero system for demo purposes"""

from typing import Dict, List
from company_data import COMPANY_INFO, TOUR_PACKAGES, HOTELS

class MockWandero:
    def __init__(self):
        self.company = COMPANY_INFO
        self.packages = TOUR_PACKAGES
        self.hotels = HOTELS
        self.conversation_state = "initial"
        self.collected_info = {}
    
    def process_email(self, client_message: str, client_state: Dict) -> str:
        """Process client email and return Wandero's response"""
        
        message_lower = client_message.lower()
        
        # Initial inquiry
        if "trip" in message_lower and "chile" in message_lower:
            self.conversation_state = "gathering_info"
            return f"""Dear {client_state.get('sender_name', 'Valued Customer')},

Thank you for your interest in visiting Chile with {self.company['name']}! 
We'd be delighted to help plan your perfect family adventure.

To create a customized itinerary, could you please provide:
- Number of travelers (adults and children with ages)
- Preferred travel dates
- Budget range
- Any special interests or requirements
- Preferred accommodation type

We specialize in family-friendly tours across {', '.join(self.company['locations'])}.

Looking forward to planning your Chilean adventure!

Best regards,
Maria Rodriguez
Travel Consultant
{self.company['name']}"""

        # Gathering details
        elif self.conversation_state == "gathering_info" and any(word in message_lower for word in ["people", "adults", "children"]):
            self.conversation_state = "proposing"
            
            # Extract family size info
            if "4" in client_message or "four" in message_lower:
                self.collected_info["travelers"] = 4
            
            # Create proposal
            package = self.packages["family_classic"]
            base_cost = package["base_price_per_person"] * 2  # 2 adults
            child_cost = package["base_price_per_person"] * (1 - package["child_discount"]) * 2  # 2 children
            total_cost = base_cost + child_cost
            
            return f"""Perfect! Based on your requirements, I'm pleased to propose our 
"{package['name']}" package:

**Duration**: {package['duration']} days / 6 nights
**Dates**: {client_state.get('travel_dates', 'July 15-22, 2024')}

**Itinerary Overview**:
{self._format_itinerary(package['itinerary'])}

**Accommodation**:
- Santiago: {self.hotels['santiago']['family']}
- Atacama: {self.hotels['atacama']['family']}

**Included**:
{self._format_list(package['includes'])}

**Total Cost**: ${total_cost:,.0f} (for 2 adults + 2 children)
*Child discount of 30% applied*

This package is perfect for families and includes child-friendly activities 
at each destination. All hotels have family suites and kids' menus.

Would you like to proceed with this itinerary, or would you prefer any modifications?

Warm regards,
Maria Rodriguez"""

        # Handle corrections/additions
        elif "forgot" in message_lower or "wait" in message_lower:
            if "allergic" in message_lower or "allergy" in message_lower:
                return """Thank you for letting me know about Jack's nut allergy. 
This is very important information!

I'll make sure to:
- Note this in all restaurant reservations
- Inform all tour guides
- Provide a list of allergy-friendly restaurants at each destination
- Include emergency medical facility information

All our partner restaurants can accommodate nut-free meals. 
Your family's safety is our top priority!

Is there anything else I should know about dietary requirements or medical needs?

Best regards,
Maria Rodriguez"""
            else:
                return "Thank you for the additional information! I'll update your travel plan accordingly."

        # Confirmation
        elif any(word in message_lower for word in ["confirm", "book", "proceed", "yes"]):
            self.conversation_state = "booking"
            return """Wonderful! I'm delighted you'd like to proceed with the booking.

**Next Steps**:
1. I'll send you a detailed invoice within the next hour
2. A 30% deposit ($1,386) is required to confirm your booking
3. Full payment is due 30 days before departure
4. You'll receive a complete travel pack with all details

**Payment Methods**: Credit card, bank transfer, or PayPal

I'll also send you:
- Pre-departure checklist
- Packing suggestions for Chile's varied climate
- Activity waivers for adventure activities

Thank you for choosing Chile Adventures! 
Your family is going to have an amazing time!

Warmest regards,
Maria Rodriguez
Travel Consultant"""

        # Default response
        else:
            return "Thank you for your message. How can I help you with your Chile travel plans?"
    
    def _format_itinerary(self, itinerary: Dict) -> str:
        return "\n".join([f"- {day}: {activity}" for day, activity in itinerary.items()])
    
    def _format_list(self, items: List) -> str:
        return "\n".join([f"✓ {item}" for item in items])