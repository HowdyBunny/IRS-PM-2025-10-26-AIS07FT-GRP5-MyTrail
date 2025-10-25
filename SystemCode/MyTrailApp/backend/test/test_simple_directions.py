#!/usr/bin/env python3
"""
Simple test for Google Routes API - get_directions interface
"""
import asyncio
import sys
import os
import webbrowser
import tempfile

# Add project path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from app.services.map.google_map_service import GoogleMapService
from app.config import settings


def create_route_visualization(route_data, title="Route Visualization"):
    """Create HTML visualization of the route"""
    polyline = route_data.get("overview_polyline", {}).get("points", "")
    viewport = route_data.get("viewport", {})
    distance = route_data.get("distance", 0)
    duration = route_data.get("duration", "0s")

    if not polyline:
        print("⚠️ No polyline data available for visualization")
        return None

    # Calculate center point for map
    if viewport and viewport.get("low") and viewport.get("high"):
        center_lat = (viewport["low"]["latitude"] + viewport["high"]["latitude"]) / 2
        center_lng = (viewport["low"]["longitude"] + viewport["high"]["longitude"]) / 2
    else:
        center_lat, center_lng = 1.2966, 103.7764  # Default to Singapore

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            #map {{ height: 600px; width: 100%; border: 1px solid #ccc; }}
            .info {{ margin: 20px 0; padding: 15px; background: #f5f5f5; border-radius: 5px; }}
            .stats {{ display: flex; gap: 20px; }}
            .stat {{ background: white; padding: 10px; border-radius: 3px; }}
        </style>
    </head>
    <body>
        <h1>{title}</h1>
        
        <div class="info">
            <div class="stats">
                <div class="stat">
                    <strong>Distance:</strong> {distance} meters ({distance/1000:.2f} km)
                </div>
                <div class="stat">
                    <strong>Duration:</strong> {duration}
                </div>
                <div class="stat">
                    <strong>Polyline Length:</strong> {len(polyline)} characters
                </div>
            </div>
        </div>
        
        <div id="map"></div>
        
        <script>
            function initMap() {{
                // Create map with better settings for route display
                const map = new google.maps.Map(document.getElementById("map"), {{
                    zoom: 13,
                    center: {{ lat: {center_lat}, lng: {center_lng} }},
                    mapTypeId: "roadmap",
                    styles: [
                        {{
                            featureType: "poi",
                            elementType: "labels",
                            stylers: [{{ visibility: "simplified" }}]
                        }}
                    ]
                }});
                
                // Decode and display polyline
                const encodedPath = "{polyline}";
                if (encodedPath) {{
                    const decodedPath = google.maps.geometry.encoding.decodePath(encodedPath);
                    console.log(`Decoded path points: ${{decodedPath.length}}`);
                    console.log('First few points:', decodedPath.slice(0, 3));
                    
                    const routePath = new google.maps.Polyline({{
                        path: decodedPath,
                        geodesic: false,  // Set to false so the path adheres to roads
                        strokeColor: "#FF6B35",  // Bright orange for better visibility
                        strokeOpacity: 0.9,
                        strokeWeight: 5,
                        zIndex: 1000,  // Ensure the route renders above other layers
                        clickable: false,
                        // Add a shadow effect to make the route clearer
                        icons: [{{
                            icon: {{
                                path: google.maps.SymbolPath.CIRCLE,
                                scale: 0
                            }},
                            repeat: '20px'
                        }}]
                    }});
                    
                    routePath.setMap(map);
                    
                    // Fit map to route bounds
                    const bounds = new google.maps.LatLngBounds();
                    decodedPath.forEach(point => bounds.extend(point));
                    map.fitBounds(bounds);
                    
                    // Add markers to show route characteristics
                    if (decodedPath.length > 0) {{
                        // Always show start/end marker (they're the same for loop routes)
                        new google.maps.Marker({{
                            position: decodedPath[0],
                            map: map,
                            title: `Start/End Point (Loop Route with ${{decodedPath.length}} points)`,
                            icon: {{
                                url: "http://maps.google.com/mapfiles/ms/icons/green-dot.png",
                                scaledSize: new google.maps.Size(32, 32)
                            }},
                            zIndex: 1001
                        }});
                        
                        // For routes with multiple points, add waypoint markers
                        if (decodedPath.length > 20) {{
                            // Add markers at quarter points to show route direction
                            const quarterPoint = Math.floor(decodedPath.length / 4);
                            const halfPoint = Math.floor(decodedPath.length / 2);
                            const threeQuarterPoint = Math.floor(decodedPath.length * 3 / 4);
                            
                            new google.maps.Marker({{
                                position: decodedPath[quarterPoint],
                                map: map,
                                title: "Route Point 1/4",
                                icon: {{
                                    url: "http://maps.google.com/mapfiles/ms/icons/yellow-dot.png",
                                    scaledSize: new google.maps.Size(24, 24)
                                }}
                            }});
                            
                            new google.maps.Marker({{
                                position: decodedPath[halfPoint],
                                map: map,
                                title: "Route Midpoint",
                                icon: {{
                                    url: "http://maps.google.com/mapfiles/ms/icons/blue-dot.png",
                                    scaledSize: new google.maps.Size(24, 24)
                                }}
                            }});
                            
                            new google.maps.Marker({{
                                position: decodedPath[threeQuarterPoint],
                                map: map,
                                title: "Route Point 3/4",
                                icon: {{
                                    url: "http://maps.google.com/mapfiles/ms/icons/purple-dot.png",
                                    scaledSize: new google.maps.Size(24, 24)
                                }}
                            }});
                        }}
                    }}
                }}
            }}
        </script>
        
        <script async defer
            src="https://maps.googleapis.com/maps/api/js?key={settings.google_maps_api_key}&libraries=geometry,places&callback=initMap">
        </script>
        
        <div class="info">
            <h3>Technical Details:</h3>
            <p><strong>Viewport:</strong> {viewport}</p>
            <p><strong>Encoded Polyline:</strong> {polyline[:100]}{'...' if len(polyline) > 100 else ''}</p>
        </div>
    </body>
    </html>
    """

    return html_content


async def test_simple_directions():
    """Test the simplest route planning"""
    # Check API Key
    api_key = settings.google_maps_api_key
    if not api_key:
        print("❌ Error: Please set google_maps_api_key in config.py")
        return False

    print("🔍 Testing the simplest get_directions functionality...")
    print(f"🔑 API Key: {api_key[:10]}...")
    print("-" * 50)

    try:
        # Create service instance
        service = GoogleMapService()

        # Simplest test: origin and destination are the same
        print("📍 Test: Origin and destination are the same")
        print("   Origin: Marina Bay Sands area (1.2834, 103.8607)")
        print("   Destination: Marina Bay Sands area (1.2834, 103.8607)")
        print("   Mode: Walking (fixed)")
        print()

        route = await service.get_directions(origin=(1.2834, 103.8607))

        print("📊 Response data:")
        print(f"   Type: {type(route)}")
        print(f"   Keys: {list(route.keys()) if isinstance(route, dict) else 'N/A'}")

        if isinstance(route, dict):
            print(f"   Total distance: {route.get('distance', 'N/A')} meters")
            print(f"   Total duration: {route.get('duration', 'N/A')}")
            polyline = route.get("overview_polyline", {}).get("points", "")
            print(f"   Polyline length: {len(polyline)} characters")

            # Display geometry information for frontend
            viewport = route.get("viewport", {})
            if viewport:
                print(f"   Viewport: {viewport}")

            # Generate visualization
            print("\n🗺️ Generating route visualization...")
            html_content = create_route_visualization(route, "Basic Route Test")
            if html_content:
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".html", delete=False
                ) as f:
                    f.write(html_content)
                    html_file = f.name
                print(f"📍 Route visualization saved to: {html_file}")
                print("🌐 Opening in browser...")
                webbrowser.open(f"file://{html_file}")
        else:
            print("❌ Response is not in dictionary format")
            return False

        print("\n✅ Basic test successful!")

        # Test waypoint functionality using find_nearby_places
        print("\n" + "=" * 50)
        print("📍 Test: Route with waypoints from find_nearby_places")
        print("   Step 1: Find nearby parks using find_nearby_places")
        print("   Step 2: Use found places as waypoints for route generation")
        print("   Origin: Marina Bay Sands area (1.2834, 103.8607)")
        print("   Destination: Marina Bay Sands area (1.2834, 103.8607)")
        print("   Mode: Walking (fixed)")
        print()

        # Step 1: Find nearby places
        print("🔍 Finding nearby parks...")
        nearby_places = await service.find_nearby_places(
            center=(1.2834, 103.8607), radius_km=2.0, categories=["park"]
        )

        if not nearby_places:
            print("❌ No nearby places found, skipping waypoint test")
            return False

        # Select first 2 places as waypoints
        selected_places = nearby_places[:2]
        waypoint_ids = [place["place_id"] for place in selected_places]

        print(
            f"✅ Found {len(nearby_places)} parks, selected {len(selected_places)} as waypoints:"
        )
        for i, place in enumerate(selected_places, 1):
            print(f"   Waypoint {i}: {place['name']} (ID: {place['place_id']})")
        print()

        # Step 2: Generate route with waypoints
        print("🗺️ Generating route with waypoints...")
        waypoint_route = await service.get_directions(
            origin=(1.2834, 103.8607), waypoints=waypoint_ids
        )

        print("📊 Waypoint route response:")
        print(f"   Type: {type(waypoint_route)}")
        print(
            f"   Keys: {list(waypoint_route.keys()) if isinstance(waypoint_route, dict) else 'N/A'}"
        )

        if isinstance(waypoint_route, dict):
            print(f"   Total distance: {waypoint_route.get('distance', 'N/A')} meters")
            print(f"   Total duration: {waypoint_route.get('duration', 'N/A')}")
            polyline = waypoint_route.get("overview_polyline", {}).get("points", "")
            print(f"   Polyline length: {len(polyline)} characters")

            # Display geometry information for frontend
            viewport = waypoint_route.get("viewport", {})
            if viewport:
                print(f"   Viewport: {viewport}")

            # Generate visualization for waypoint route
            print("\n🗺️ Generating waypoint route visualization...")
            waypoint_names = [place["name"] for place in selected_places]
            title = f"Waypoint Route: {' → '.join(waypoint_names)}"
            html_content = create_route_visualization(waypoint_route, title)
            if html_content:
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".html", delete=False
                ) as f:
                    f.write(html_content)
                    html_file = f.name
                print(f"📍 Waypoint route visualization saved to: {html_file}")
                print("🌐 Opening in browser...")
                webbrowser.open(f"file://{html_file}")
        else:
            print("❌ Waypoint route response is not in dictionary format")
            return False

        print("\n✅ Waypoint test successful!")
        return True

    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        print(f"Error type: {type(e).__name__}")

        # Provide error diagnosis
        error_msg = str(e).lower()
        if "api key" in error_msg or "invalid" in error_msg:
            print("\n💡 Diagnosis: API Key issue")
            print("  1. Check if API Key is correct")
            print("  2. Confirm Routes API service is enabled")
        elif "quota" in error_msg or "limit" in error_msg:
            print("\n💡 Diagnosis: API quota issue")
            print("  1. Check API quota usage")
        elif "network" in error_msg or "connection" in error_msg:
            print("\n💡 Diagnosis: Network issue")
            print("  1. Check network connection")
        else:
            print(f"\n💡 Diagnosis: Other error - {type(e).__name__}")

        return False


async def main():
    """Main function"""
    success = await test_simple_directions()

    if success:
        print("\n✅ Simple test passed!")
        sys.exit(0)
    else:
        print("\n❌ Simple test failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
