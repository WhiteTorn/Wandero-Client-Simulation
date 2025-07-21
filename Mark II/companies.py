COMPANIES = {
    "luxury_chile": {
        "name": "Chile Luxury Escapes",
        "type": "luxury",
        "specialties": ["5-star hotels", "private tours", "gourmet dining", "helicopter tours"],
        "destinations": ["Santiago", "Wine Valleys", "Atacama", "Patagonia"],
        "price_range": {"min": 500, "max": 1500, "per_day": True},
        "unique_selling_points": [
            "Exclusive access to private vineyards",
            "Michelin-starred dining experiences",
            "Personal butler service",
            "Private jet transfers available"
        ],
        "max_discount": 0.1,  # Maximum 10% discount
        "target_audience": "affluent travelers seeking exclusive experiences"
    },
    
    "chile_adventures": {
        "name": "Chile Adventure Tours",
        "type": "adventure",
        "specialties": ["trekking", "climbing", "rafting", "wildlife"],
        "destinations": ["Torres del Paine", "Atacama", "Lake District", "Patagonia"],
        "price_range": {"min": 200, "max": 400, "per_day": True},
        "unique_selling_points": [
            "Expert adventure guides",
            "Small group sizes (max 8)",
            "All equipment included",
            "Off-the-beaten-path experiences"
        ],
        "max_discount": 0.15,  # Maximum 15% discount
        "target_audience": "active travelers seeking authentic adventures"
    },
    
    "family_adventures": {
        "name": "Family Fun Chile",
        "type": "family",
        "specialties": ["family tours", "educational experiences", "safe adventures", "flexible timing"],
        "destinations": ["Santiago", "Valparaiso", "Lake District", "Easter Island"],
        "price_range": {"min": 300, "max": 500, "per_day": True},
        "unique_selling_points": [
            "Kid-friendly guides",
            "Family rooms guaranteed",
            "Children's activities included",
            "Flexible meal times",
            "24/7 medical support"
        ],
        "max_discount": 0.2,  # Maximum 20% discount for families
        "target_audience": "families with children seeking safe, fun experiences"
    },
    
    "patagonia_tours": {
        "name": "Patagonia Wonders",
        "type": "standard",
        "specialties": ["classic tours", "nature", "photography", "cultural experiences"],
        "destinations": ["Patagonia", "Lake District", "Chiloe", "Marble Caves"],
        "price_range": {"min": 250, "max": 450, "per_day": True},
        "unique_selling_points": [
            "Local expert guides",
            "Sustainable tourism certified",
            "Small groups",
            "Authentic local experiences"
        ],
        "max_discount": 0.15,
        "target_audience": "travelers seeking authentic Patagonian experiences"
    }
}