from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from app.models.request import QueryRequest, RouteCriteria
from app.models.response import RouteResponse
from app.models.feedback import RouteFeedback
from app.services.route_service import RouteService
from app.services.nlp_service import NLPService
from app.services.feedback_service import FeedbackService
from app.config import settings

app = FastAPI(
    title="MyTrail API",
    description="Intelligent route generation API",
    version=settings.api_version,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

route_service = RouteService()
nlp_service = NLPService()

# Initialize feedback service with error handling
try:
    feedback_service = FeedbackService()
    print("✅ Feedback service initialized")
except Exception as e:
    print(f"⚠️ Failed to initialize feedback service: {e}")
    feedback_service = None


# main api
@app.post("/api/v1/routes/query", response_model=RouteResponse)
async def suggest_routes_from_query(request: QueryRequest):
    """Generate routes based on natural language query and user location"""
    try:
        criteria = await nlp_service.parse_query(request.query, request.center)
        response = await route_service.generate_routes(criteria)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Route generation failed: {str(e)}"
        )


# For testing generation
@app.post("/api/v1/routes/suggest", response_model=RouteResponse)
async def suggest_routes(criteria: RouteCriteria):
    """Generate routes based on structured criteria"""
    try:
        response = await route_service.generate_routes(criteria)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Route generation failed: {str(e)}"
        )


@app.post("/parse", response_model=RouteCriteria)
async def parse_route_criteria(request: QueryRequest):
    """Expose the NLP parsing pipeline as an API endpoint."""
    try:
        return await nlp_service.parse_query(request.query, request.center)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parsing failed: {str(e)}")


@app.post("/api/v1/feedback")
async def submit_feedback(routes: List[RouteFeedback]):
    """Submit user feedback for route selection"""
    if feedback_service is None:
        return {
            "status": "warning", 
            "message": "Feedback service not available (MongoDB not connected). Feedback not stored."
        }
    
    try:
        success = feedback_service.store_feedback(routes)
        if success:
            if feedback_service.is_available():
                return {"status": "success", "message": "Feedback stored successfully"}
            else:
                return {
                    "status": "warning", 
                    "message": "Feedback received but not stored (MongoDB unavailable)"
                }
        else:
            raise HTTPException(status_code=500, detail="Failed to store feedback")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Feedback submission failed: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check"""
    return {"status": "healthy", "version": settings.api_version}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
