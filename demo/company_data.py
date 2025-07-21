"""Company and tour information for the demo"""

COMPANY_INFO = {
    "name": "Chile Adventures Ltd.",
    "email": "contact@chileadventures.com",
    "country": "Chile",
    "specialties": ["Family tours", "Adventure travel", "Cultural experiences"],
    "locations": ["Santiago", "Atacama Desert", "Patagonia", "Valparaíso", "Easter Island"]
}

TOUR_PACKAGES = {
    "family_classic": {
        "name": "Classic Chile Family Adventure",
        "duration": 7,
        "base_price_per_person": 1200,
        "child_discount": 0.3,
        "includes": [
            "Airport transfers",
            "Hotel accommodation (4-star)",
            "Daily breakfast",
            "Guided tours",
            "Entrance fees"
        ],
        "itinerary": {
            "Day 1": "Arrival in Santiago - City tour",
            "Day 2": "Valparaíso coastal excursion",
            "Day 3-4": "Fly to Atacama - Desert adventures",
            "Day 5": "Salt flats and flamingo watching",
            "Day 6": "Return to Santiago",
            "Day 7": "Departure"
        }
    },
    "adventure_seeker": {
        "name": "Chile Extreme Adventure",
        "duration": 10,
        "base_price_per_person": 2500,
        "includes": ["All activities", "Professional guides", "Equipment"]
    }
}

HOTELS = {
    "santiago": {
        "family": "Hotel Plaza San Francisco (Family Suite)",
        "budget": "Happy House Hostel",
        "luxury": "The Ritz-Carlton Santiago"
    },
    "atacama": {
        "family": "Hotel Cumbres San Pedro de Atacama",
        "budget": "Hostal Pueblo de Tierra",
        "luxury": "Explora Atacama"
    }
}