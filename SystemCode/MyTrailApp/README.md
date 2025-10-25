# Project Name: MyTrail
### Brief Description:
MyTrail is an application that uses intelligent algorithms to generate diverse routes and record your exploration journey. You can freely enter any conditions you care about—such as passing through parks, staying in pet-friendly zones, or avoiding crowds. The system applies intelligent reasoning to instantly generate multiple routes that match your requirements, each ready for one-click preview and tracking. You can not only discover fresh corners of the city but also capture every health metric from the experience.
### Keywords:
Exercise, urban exploration, newcomers, outdoor journaling
## Project Background:
As healthy living becomes a mainstream value and public figures continue to promote outdoor activities, running, leisurely walks, and city exploration have surged in popularity over the past five years. Users want both performance tracking and a way to discover urban landscapes. This demand has spawned an ecosystem of tools that help people train intelligently and expand their social circles. Many rely on apps to log their workout routes or exploration footprints. These apps typically track duration, speed, calories burned, and other data, helping users evaluate each outing. Some also offer social feeds or communities where users share their progress, highlight achievements, and build their reputation.
### Market Research:
Several well-known apps dominate the market, including Keep, Strava, and AllTrails, with App Store ratings of 4.8, 4.8, and 4.9 respectively. User reviews often praise their clean interfaces, robust foundational features, and valuable extras such as training guides or instructional videos. For example, Keep integrates a store and community features that keep users engaged and learning. To boost retention, Keep rewards users with virtual or physical medals for completing challenges. AllTrails provides a streamlined interface with scenic routes and elevation profiles. However, some users complain that Keep’s interface feels cluttered and distracting, and intrusive ads can be frustrating. When it comes to route logging, users can either record spontaneous activities or choose from a finite set of predefined routes stored in each app’s database. A few apps let users manually define points on a map to generate a route.
### User Pain Points Addressed by MyTrail:
Every time a user opens the app, they can provide specific or fuzzy keywords and receive multiple system-generated routes in real time. Each outing is unique, reducing input friction while satisfying the desire to explore the city. Example prompts include: “I want to walk within 5 km of my current location, short on time, avoid crowded areas, and pass through a park because I’m bringing my dog,” or “Plan a 3 km run with at least 40 m of elevation gain that takes me past the shoreline.” The system interprets these needs automatically, avoiding manual point-and-click inputs on a map. Generating multiple candidate routes ensures variety. In contrast, Keep, Strava, and AllTrails focus on recording or predefined route libraries; if users want an on-the-spot route tailored to their mood or constraints, they still have to select it manually or rely on existing entries.
### Target Customers & Market Demand Analysis:
MyTrail serves a broad age range of outdoor enthusiasts who want to log their routes. The product introduces an innovative input mechanism that simplifies how users articulate their needs. It is especially helpful for urban explorers, newcomers to a city, and travelers, and it includes optimizations for users with pets.  
Primary persona: urban residents aged 20–45 who walk or run 2–5 times a week and value both experience and efficiency. Secondary segments: pet owners, weekend adventurers, short-term visitors, exchange students, and similar groups.  
Future B2B prospects include city tourism boards, community event organizers, and branded challenge partners.

While most fitness apps offer similar baseline features (route logging), there remains room for improvement around user-specific optimization, onboarding, and ease of use. MyTrail differentiates itself by using intelligent route recommendation: algorithms transform user-submitted criteria into constraints and generate custom walking routes on demand, rather than relying on a static route database. The interface is streamlined to reduce friction. For city newcomers or travelers, MyTrail offers an ideal tool for discovery and maintaining a sense of novelty.

Potential competitors: Keep, Strava, AllTrails, and other incumbents have amassed large user bases. Switching away from these familiar platforms is difficult unless a new product offers strong differentiation and value. The route-tracking segment is nearing saturation, and the trend is toward community-driven growth. Yet that direction can lead to bloated apps.
## Project Scope
MyTrail is a market-oriented MVP initially targeting Singapore. The project is expected to leverage the following intelligent reasoning techniques:
1. Convert user selections or inputs into structured values that act as constraints for route optimization. This involves natural language processing (NLP) to translate free text into constraint JSON, primarily using rule templates, dictionaries, and regular expressions, with an LLM as fallback. Slot-based NLU design covers distance/duration, loop vs. out-and-back, inclusion/exclusion categories, pet friendliness, elevation thresholds, time of day, etc. If parsing fails, fall back to defaults and notify the user.
2. Use the user’s location as the center for geospatial searches and generate recommendations via collaborative filtering or matrix factorization.
3. Produce routes that start and end at the same point and pass through constraint landmarks, using methods such as multi-objective evolutionary algorithms (e.g., NSGA-II), constrained shortest paths, or custom routing engines. After evaluation, classic genetic algorithms may not suit real-time routing; if used later, curated routes can be cached.

## Current Limitations (TBC)
1. Interaction challenges while running inference or machine learning workflows.
2. Usage limits on public map APIs.
3. User authentication is not yet implemented.
**...**
## Data Collection and Preprocessing:
MyTrail uses open OpenStreetMap and Google Maps APIs.
- Map data: built with OSMnx, GraphHopper, Valhalla, or pgRouting.
- Elevation data: prefer Google Maps; if unavailable, use SRTM or Copernicus DEM, which are sufficient for city-scale elevation and cumulative gain calculations.
- Pet-friendly areas: scraped and processed from Dog Map or derived from `dog=*` tags in OSM.
- Crowd density: challenging to obtain directly. Potential sources include Veraset/SafeGraph, Strava Metro, or Foursquare. Alternative proxies include POI density, time-of-day patterns, road betweenness centrality, and the intensity of events or commercial zones.
- Optional (administrative boundaries and geographic rasters): Natural Earth, OSM boundaries, EPSG coordinate systems.
## System Design:
Flowchart (TBC). Recommend using draw.io for diagramming.
1. Frontend: Flutter with Flutter Map integration.
2. Backend: FastAPI
