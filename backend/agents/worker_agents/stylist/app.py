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
from typing import Optional, List, Dict, Any
import uvicorn
import uuid
from datetime import datetime
import redis_utils
import os
from groq import Groq

# Type aliases
ProductDict = Dict[str, Any]

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

def _build_complementary_specs(product: ProductDict) -> List[Dict[str, Any]]:
    """Derive complementary product filters based on the purchased item."""

    name_lower = (product.get("name") or "").lower()
    subcategory_lower = (product.get("subcategory") or "").lower()
    category_lower = (product.get("category") or "").lower()

    specs: List[Dict[str, Any]] = []

    if any(keyword in name_lower for keyword in ["jean", "denim"]) or "bottom" in subcategory_lower:
        specs = [
            {
                "category": "Apparel",
                "keywords": ["topwear", "t-shirt", "shirt", "tee"],
                "reason": "{item} sharpens the upper half and lets your {purchase} stay the hero piece.",
            },
            {
                "category": "Footwear",
                "keywords": ["shoe", "sneaker", "trainer"],
                "reason": "{item} grounds the denim and keeps the palette clean for a weekend-ready look.",
            },
            {
                "category": "Apparel",
                "keywords": ["jacket", "hoodie", "outerwear", "sweatshirt"],
                "reason": "Layering with {item} adds structure and warmth without overpowering your {purchase}.",
            },
        ]
    elif "top" in subcategory_lower or any(keyword in name_lower for keyword in ["tee", "shirt", "top"]):
        specs = [
            {
                "category": "Apparel",
                "keywords": ["bottom", "jean", "trouser", "skirt"],
                "reason": "{item} balances the proportions of {purchase} and keeps the silhouette streamlined.",
            },
            {
                "category": "Footwear",
                "keywords": ["shoe", "sneaker", "heel", "loafer"],
                "reason": "Finish the outfit with {item} to echo the colour accents in {purchase}.",
            },
            {
                "category": "Accessories",
                "keywords": ["bag", "belt", "cap", "hat"],
                "reason": "A hint of {item} adds polish and ties the whole look together.",
            },
        ]
    elif "shoe" in name_lower or "footwear" in category_lower:
        specs = [
            {
                "category": "Apparel",
                "keywords": ["bottom", "jean", "jogger", "track"],
                "reason": "Offset the sneakers with {item} for an effortless athleisure mood.",
            },
            {
                "category": "Apparel",
                "keywords": ["topwear", "hoodie", "jacket", "tee"],
                "reason": "{item} mirrors the sporty energy of your {purchase} and keeps the look cohesive.",
            },
            {
                "category": "Accessories",
                "keywords": ["bag", "sling", "cap"],
                "reason": "Add {item} so your footwear stands out while the accessories stay functional.",
            },
        ]
    else:
        specs = [
            {
                "category": "Apparel",
                "keywords": ["layer", "jacket", "cardigan", "shrug"],
                "reason": "{item} adds depth and works seamlessly with {purchase} for multiple occasions.",
            },
            {
                "category": "Footwear",
                "keywords": ["shoe", "sneaker", "loafer", "heel"],
                "reason": "Pair with {item} to keep the outfit grounded and versatile.",
            },
            {
                "category": "Accessories",
                "keywords": ["bag", "watch", "belt", "cap"],
                "reason": "Introduce {item} for a refined finishing touch without overpowering your {purchase}.",
            },
        ]

    return specs


def _generate_styling_tips(purchase_name: str, suggestions: List[Dict[str, str]]) -> List[str]:
    tips: List[str] = []

    if not suggestions:
        return tips

    tips.append(f"Half-tuck the top pick to showcase the structure of your {purchase_name}.")

    if len(suggestions) >= 2:
        tips.append(f"Use {suggestions[1]['name']} to keep colours consistent from head to toe.")

    if len(suggestions) >= 3:
        tips.append(f"Finish with {suggestions[2]['name']} so the outfit transitions from day to evening effortlessly.")

    if not tips:
        tips.append(f"Let your {purchase_name} shine and keep other pieces streamlined.")

    return tips


def get_ai_outfit_suggestions(product: ProductDict) -> Dict:
    """Curate in-stock outfit suggestions grounded in catalogue and inventory data."""

    purchase_name = product.get("name", "your purchase")
    purchase_sku = product.get("sku")

    specs = _build_complementary_specs(product)
    used_skus = {purchase_sku}
    recommended_products: List[Dict[str, str]] = []

    for spec in specs:
        matches = redis_utils.find_in_stock_products(
            category=spec.get("category"),
            subcategory_keywords=spec.get("keywords"),
            exclude_skus=used_skus,
            limit=1
        )
        if not matches:
            continue

        item = matches[0]
        used_skus.add(item['sku'])
        reason = spec['reason'].format(item=item['name'], purchase=purchase_name)
        recommended_products.append({
            "sku": item['sku'],
            "name": item['name'],
            "reason": reason
        })

    if not recommended_products:
        # fallback to any in-stock items
        fallback_items = redis_utils.find_in_stock_products(exclude_skus=used_skus, limit=3)
        for item in fallback_items:
            recommended_products.append({
                "sku": item['sku'],
                "name": item['name'],
                "reason": f"{item['name']} is in stock and complements {purchase_name} seamlessly."
            })

    styling_tips = _generate_styling_tips(purchase_name, recommended_products)

    return {
        "recommended_products": recommended_products,
        "styling_tips": styling_tips
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
        
        suggestions = get_ai_outfit_suggestions(product_details)
        
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
