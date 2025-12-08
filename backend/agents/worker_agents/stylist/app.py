"""
Post-Purchase Stylist Agent - FastAPI Server
AI-powered styling suggestions, outfit combinations, and care instructions

Endpoints:
- POST /stylist/outfit-suggestions (AI-generated)
- POST /stylist/care-instructions
- POST /stylist/occasion-styling (AI-generated)
- POST /stylist/seasonal-styling (AI-generated)
- POST /stylist/fit-feedback
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import uvicorn
import uuid
from datetime import datetime
import redis_utils
import os
from groq import Groq

# Initialize Groq AI client
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

app = FastAPI(
    title="Post-Purchase Stylist Agent",
    description="AI-powered styling recommendations and product care guidance",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# REQUEST/RESPONSE MODELS
# ==========================================

class OutfitRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    product_sku: str = Field(..., description="Product SKU purchased")
    product_name: str = Field(..., description="Product name")
    category: str = Field(..., description="Product category")
    color: Optional[str] = Field(None, description="Product color")
    brand: Optional[str] = Field(None, description="Product brand")


class CareInstructionsRequest(BaseModel):
    product_sku: str = Field(..., description="Product SKU")
    material: str = Field(..., description="Product material (cotton, linen, silk, etc.)")


class OccasionStylingRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    product_sku: str = Field(..., description="Product SKU")
    product_name: str = Field(..., description="Product name")


class SeasonalStylingRequest(BaseModel):
    product_sku: str = Field(..., description="Product SKU")
    product_name: str = Field(..., description="Product name")
    product_type: str = Field(..., description="Product type (jacket, dress, etc.)")


class FitFeedbackRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    product_sku: str = Field(..., description="Product SKU")
    size_purchased: str = Field(..., description="Size purchased")
    fit_rating: str = Field(..., description="too_tight, perfect, too_loose")
    length_feedback: Optional[str] = Field(None, description="too_short, perfect, too_long")
    comments: Optional[str] = Field(None, description="Additional comments")


# ==========================================
# AI STYLING ENGINE
# ==========================================

def get_ai_outfit_suggestions(product_name: str, category: str, color: str = None, brand: str = None, purchased_sku: str = None) -> Dict:
    """Use AI to generate personalized outfit suggestions from actual product catalog"""
    
    # Get products from our catalog to recommend
    available_products = redis_utils.get_all_products()
    
    # Sample products by category for recommendations
    apparel_products = available_products[available_products['category'] == 'Apparel'].sample(n=min(10, len(available_products)))
    footwear_products = available_products[available_products['category'] == 'Footwear'].sample(n=min(5, len(available_products)))
    
    # Build product list for AI context
    product_context = "Available products in our store:\n"
    product_context += "\nApparel:\n"
    for _, p in apparel_products.iterrows():
        product_context += f"- {p['ProductDisplayName']} (SKU: {p['sku']}, Price: ₹{p['price']})\n"
    
    product_context += "\nFootwear:\n"
    for _, p in footwear_products.iterrows():
        product_context += f"- {p['ProductDisplayName']} (SKU: {p['sku']}, Price: ₹{p['price']})\n"
    
    color_info = f", color: {color}" if color else ""
    brand_info = f", brand: {brand}" if brand else ""
    
    prompt = f"""You are a fashion stylist for an e-commerce store. Customer just purchased: {product_name} (category: {category}{color_info}{brand_info}).

{product_context}

Recommend products from ONLY the list above. Return in this EXACT JSON format:
{{
    "recommended_products": [
        {{"sku": "SKU000XXX", "name": "Product Name", "reason": "why it pairs well"}},
        {{"sku": "SKU000XXX", "name": "Product Name", "reason": "why it pairs well"}}
    ],
    "styling_tips": ["tip 1", "tip 2", "tip 3"]
}}

Rules:
- Recommend 3-5 products from the available list ONLY
- Include SKU, product name, and styling reason
- Be specific about how items pair together
- Consider Indian fashion context
- Only return valid JSON"""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1024
        )
        
        import json
        result = json.loads(response.choices[0].message.content)
        return result
        
    except Exception as e:
        # Fallback: return products from same category
        fallback_products = redis_utils.search_products_by_category(category, limit=3)
        return {
            "recommended_products": [
                {"sku": p["sku"], "name": p["name"], "reason": "Complements your purchase"}
                for p in fallback_products
            ],
            "styling_tips": ["Mix and match with your wardrobe", "Layer for different occasions"]
        }


def get_care_instructions(material: str) -> Dict:
    """Get care and washing instructions"""
    
    care_db = {
        "cotton": {
            "washing": "Machine wash cold with like colors",
            "drying": "Tumble dry low or hang dry",
            "ironing": "Iron on medium heat while slightly damp",
            "storage": "Store in cool, dry place",
            "tips": ["Avoid bleach", "Wash inside out to preserve color"]
        },
        "linen": {
            "washing": "Hand wash or machine wash cold on gentle cycle",
            "drying": "Hang dry - do not tumble dry",
            "ironing": "Iron on low to medium heat while still damp",
            "storage": "Hang or fold loosely to avoid wrinkles",
            "tips": ["Linen softens with each wash", "Wrinkles are part of linen's charm"]
        },
        "silk": {
            "washing": "Dry clean recommended or hand wash in cold water",
            "drying": "Lay flat to dry away from direct sunlight",
            "ironing": "Iron on low heat with pressing cloth",
            "storage": "Store in breathable garment bag",
            "tips": ["Never wring silk", "Use mild detergent"]
        },
        "wool": {
            "washing": "Dry clean or hand wash in cold water",
            "drying": "Lay flat to dry - never hang wet wool",
            "ironing": "Steam or iron on low with pressing cloth",
            "storage": "Store with mothballs in cool place",
            "tips": ["Never use hot water", "Avoid direct heat"]
        },
        "polyester": {
            "washing": "Machine wash warm",
            "drying": "Tumble dry low",
            "ironing": "Iron on low heat if needed",
            "storage": "Standard closet storage",
            "tips": ["Wrinkle-resistant", "Quick-drying fabric"]
        },
        "denim": {
            "washing": "Turn inside out, wash cold every 5-6 wears",
            "drying": "Air dry or tumble dry low",
            "ironing": "Iron on high heat if needed",
            "storage": "Hang or fold",
            "tips": ["Washing less preserves color", "Spot clean when possible"]
        }
    }
    
    material_lower = material.lower()
    for key in care_db:
        if key in material_lower:
            return care_db[key]
    
    return {
        "washing": "Follow care label instructions",
        "drying": "Air dry recommended",
        "ironing": "Iron on appropriate heat setting",
        "storage": "Store in cool, dry place",
        "tips": ["Always check garment care label"]
    }


def get_ai_occasion_styling(product_name: str, category: str) -> Dict:
    """Use AI to generate occasion-specific styling"""
    
    prompt = f"""You are a fashion stylist. The customer bought: {product_name} (category: {category}).

Give styling ideas for 3 occasions in this EXACT JSON format:
{{
    "office_wear": {{
        "description": "brief description",
        "styling": "how to style it",
        "accessories": ["item 1", "item 2"],
        "tips": "one styling tip"
    }},
    "casual_wear": {{
        "description": "brief description",
        "styling": "how to style it",
        "accessories": ["item 1", "item 2"],
        "tips": "one styling tip"
    }},
    "party_wear": {{
        "description": "brief description",
        "styling": "how to style it",
        "accessories": ["item 1", "item 2"],
        "tips": "one styling tip"
    }}
}}

Make it practical and wearable. Only return JSON."""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1024
        )
        
        import json
        result = json.loads(response.choices[0].message.content)
        return result
        
    except Exception as e:
        return {
            "office_wear": {"description": "Professional", "styling": "Keep it simple", "accessories": ["Watch"], "tips": "Minimal is key"},
            "casual_wear": {"description": "Comfortable", "styling": "Pair with basics", "accessories": ["Sunglasses"], "tips": "Stay relaxed"},
            "party_wear": {"description": "Glamorous", "styling": "Add shine", "accessories": ["Clutch"], "tips": "Be confident"}
        }


def get_ai_seasonal_styling(product_name: str, product_type: str) -> Dict:
    """Use AI to generate seasonal styling ideas"""
    
    prompt = f"""You are a fashion stylist. The customer bought: {product_name} (type: {product_type}).

Give seasonal styling ideas in this EXACT JSON format:
{{
    "winter": "how to style in winter",
    "spring": "how to style in spring",
    "summer": "how to style in summer",
    "monsoon": "how to style in monsoon"
}}

Make it specific to Indian weather. Only return JSON."""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=800
        )
        
        import json
        result = json.loads(response.choices[0].message.content)
        return result
        
    except Exception as e:
        return {
            "winter": "Layer appropriately for warmth",
            "spring": "Light and breezy styling",
            "summer": "Keep it cool and comfortable",
            "monsoon": "Weather-appropriate choices"
        }


# ==========================================
# ROUTES
# ==========================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Post-Purchase Stylist Agent",
        "status": "running",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/stylist/outfit-suggestions")
async def get_outfit_suggestions_api(request: OutfitRequest):
    """
    Get AI-generated outfit suggestions based on purchased product
    Recommends products from actual catalog (products.csv)
    """
    try:
        # Get product details
        product_details = redis_utils.get_product_details(request.product_sku)
        
        if not product_details:
            raise HTTPException(status_code=404, detail="Product not found in catalog")
        
        suggestions = get_ai_outfit_suggestions(
            product_details['name'], 
            product_details['category'],
            product_details['color'],
            product_details['brand'],
            request.product_sku
        )
        
        recommendation_id = f"STY_{uuid.uuid4().hex[:12].upper()}"
        
        response = {
            "success": True,
            "recommendation_id": recommendation_id,
            "purchased_product": product_details,
            "recommendations": suggestions,
            "message": f"AI styling recommendations from our product catalog",
            "timestamp": datetime.now().isoformat()
        }
        
        # Store recommendation
        redis_utils.store_styling_recommendation(recommendation_id, {
            "user_id": request.user_id,
            "product_sku": request.product_sku,
            "type": "outfit_suggestions",
            "timestamp": datetime.now().isoformat()
        })
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stylist/care-instructions")
async def get_care_instructions_api(request: CareInstructionsRequest):
    """
    Get care and washing instructions based on material
    Helps maintain product quality and extend lifetime
    """
    try:
        instructions = get_care_instructions(request.material)
        
        return {
            "success": True,
            "material": request.material,
            "care_instructions": instructions,
            "message": f"Care guide for your {request.material} product",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stylist/occasion-styling")
async def get_occasion_styling_api(request: OccasionStylingRequest):
    """
    Get AI-generated styling ideas for different occasions
    Office, Casual, Party wear suggestions
    """
    try:
        occasions = get_ai_occasion_styling(request.product_name, "apparel")
        
        return {
            "success": True,
            "product": request.product_name,
            "occasion_styling": occasions,
            "message": "Groq AI occasion styling for your purchase",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stylist/seasonal-styling")
async def get_seasonal_styling_api(request: SeasonalStylingRequest):
    """
    Get AI-generated seasonal styling tips
    How to wear the product across different seasons
    """
    try:
        seasonal_tips = get_ai_seasonal_styling(request.product_name, request.product_type)
        
        return {
            "success": True,
            "product": request.product_name,
            "seasonal_styling": seasonal_tips,
            "message": "Groq AI seasonal styling guide",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stylist/fit-feedback")
async def submit_fit_feedback(request: FitFeedbackRequest):
    """
    Submit fit feedback for future size recommendations
    Learns from user's fit preferences
    """
    try:
        feedback_data = {
            "user_id": request.user_id,
            "product_sku": request.product_sku,
            "size_purchased": request.size_purchased,
            "fit_rating": request.fit_rating,
            "length_feedback": request.length_feedback or "not_specified",
            "comments": request.comments or "",
            "timestamp": datetime.now().isoformat()
        }
        
        redis_utils.store_user_fit_feedback(
            request.user_id,
            request.product_sku,
            feedback_data
        )
        
        # Generate recommendation for next purchase
        size_recommendation = request.size_purchased
        if request.fit_rating == "too_tight":
            size_recommendation = "Consider sizing up next time"
        elif request.fit_rating == "too_loose":
            size_recommendation = "Consider sizing down next time"
        else:
            size_recommendation = "This size works well for you"
        
        return {
            "success": True,
            "message": "Thank you for your feedback!",
            "size_recommendation": size_recommendation,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8006)
