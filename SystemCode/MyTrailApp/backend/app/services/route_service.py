"""
Main route generation service - simplified mock implementation
Integrates generation, ranking, reranking, and response building modules
"""

from app.models.request import RouteCriteria
from app.models.response import RouteResponse
from app.services.route.generation_service import RouteGenerationService
from app.services.route.response_builder import ResponseBuilderService
from app.services.route.ranking_service import RouteRankingService



class RouteService:
    """
    Main route generation service - simplified four-layer processing flow

    Architecture: Candidate generation → Ranking → Reranking (diversity) → Response building
    """

    def __init__(self):
        self.generation_service = RouteGenerationService()
        self.response_builder = ResponseBuilderService()
        self.ranking_service = RouteRankingService()
        

    async def generate_routes(self, criteria: RouteCriteria) -> RouteResponse:
        """
        Main route generation process - simplified mock implementation
        """
        # Step 1: Generate candidate routes
        candidate_routes = await self.generation_service.generate_candidate_routes(
            criteria
        )

        if not candidate_routes:
            # If no candidate routes generated, return empty result
            return self.response_builder.build_response([])

        # Step 2: Skip ranking for now, directly use candidate routes
        ranked_routes = self.ranking_service.rank_routes(candidate_routes)

        # Step 3: Cluster routes to provide diversity metadata
        # self.clustering_service.cluster_routes(candidate_routes)
        
        # Step 4: Build response (limit to first 5 routes)
        response = self.response_builder.build_response(ranked_routes[:5])
        
        # Add criteria to response for feedback training
        response.criteria = criteria.dict()

        return response
