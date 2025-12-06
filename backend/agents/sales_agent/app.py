import logging
import uuid
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Sales Agent API",
    description="API for handling sales agent conversations",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class MessageRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User message to the sales agent")
    session_token: Optional[str] = Field(None, description="Session token for conversation continuity")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "I'm interested in your product",
                "session_token": "abc123-def456",
                "metadata": {"user_id": "user_001", "source": "web"}
            }
        }


class ResumeSessionRequest(BaseModel):
    session_token: str = Field(..., min_length=1, description="Session token to resume")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "session_token": "abc123-def456",
                "metadata": {"user_id": "user_001"}
            }
        }


class AgentResponse(BaseModel):
    reply: str = Field(..., description="Agent's response message")
    session_token: str = Field(..., description="Session token for tracking conversation")
    timestamp: str = Field(..., description="Response timestamp")
    metadata: dict = Field(default_factory=dict, description="Additional response metadata")


# Middleware for logging requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Log incoming request
    logger.info(f"Incoming request: {request.method} {request.url.path}")
    
    # Get request body for logging (be careful with large payloads in production)
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.body()
            logger.info(f"Request body: {body.decode('utf-8')[:500]}")  # Limit log size
            
            # Important: Store body for route handler to access
            async def receive():
                return {"type": "http.request", "body": body}
            request._receive = receive
        except Exception as e:
            logger.error(f"Error reading request body: {e}")
    
    # Process request
    response = await call_next(request)
    
    # Log response status
    logger.info(f"Response status: {response.status_code}")
    
    return response


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "detail": exc.errors(),
            "message": "Invalid request payload"
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please try again later."
        }
    )


# API Endpoints
@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "Sales Agent API",
        "version": "1.0.0"
    }


@app.post("/api/message", response_model=AgentResponse)
async def handle_message(request: MessageRequest):
    """
    Handle incoming user messages and generate agent responses
    
    This is a placeholder endpoint that returns dummy responses.
    In production, this would integrate with LLM logic.
    """
    logger.info(f"Processing message: '{request.message[:50]}...'")
    
    # Generate or reuse session token
    session_token = request.session_token or str(uuid.uuid4())
    
    # Dummy response logic (replace with actual LLM integration later)
    response = AgentResponse(
        reply=f"This is a placeholder response from SalesAgent. You said: '{request.message}'. How can I help you further?",
        session_token=session_token,
        timestamp=datetime.utcnow().isoformat(),
        metadata={
            "agent_type": "sales",
            "processed": True,
            "original_metadata": request.metadata
        }
    )
    
    logger.info(f"Generated response for session: {session_token}")
    
    return response


@app.post("/api/resume_session", response_model=AgentResponse)
async def resume_session(request: ResumeSessionRequest):
    """
    Resume an existing conversation session
    
    This is a placeholder endpoint that simulates session resumption.
    In production, this would load conversation history and context.
    """
    logger.info(f"Resuming session: {request.session_token}")
    
    # Dummy session resumption logic
    response = AgentResponse(
        reply=f"Welcome back! Your session {request.session_token} has been resumed. How can I assist you today?",
        session_token=request.session_token,
        timestamp=datetime.utcnow().isoformat(),
        metadata={
            "agent_type": "sales",
            "session_resumed": True,
            "original_metadata": request.metadata
        }
    )
    
    logger.info(f"Session resumed successfully: {request.session_token}")
    
    return response


# Run the application
if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
