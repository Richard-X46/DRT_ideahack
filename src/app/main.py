import json
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import folium
from pydantic import BaseModel
from starlette.requests import Request
from fastapi.middleware.cors import CORSMiddleware
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))  # Adjust the path to your project structure
import src.data.drt_gtfs as gtfs
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),  # Console output
        logging.FileHandler("app.log")  # Log to file
    ]
)


logger = logging.getLogger(__name__)  # Create a logger for this module

# Initialize FastAPI app
app = FastAPI()

origins = [
    "http://localhost:3000",  # Front-end URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allows the front-end to access FastAPI API
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create a Pydantic model to receive source and destination information
class RouteRequest(BaseModel):
    source: str
    destination: str

# Set up the static files and templates
app.mount("/static", StaticFiles(directory="src/app/static"), name="static")
templates = Jinja2Templates(directory="src/app/templates")

# Serve the index.html file (first page with the image and "Check Out" button)
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    try:
        logger.info("Rendering index.html page.")
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        logger.error(f"Error loading the index page: {str(e)}")
        return HTMLResponse(content=f"<h1>Error loading the page: {str(e)}</h1>", status_code=500)


@app.get("/secondPage", response_class=HTMLResponse)
async def second_page(request: Request):
    try:
        logger.info("Rendering secondPage.html.")
        return templates.TemplateResponse("secondPage.html", {"request": request})
    except Exception as e:
        logger.error(f"Error loading the second page: {str(e)}")
        return HTMLResponse(content=f"<h1>Error on second page: {str(e)}</h1>", status_code=500)


@app.get("/locations")
async def get_locations():
    try:
        logger.info("Fetching locations from geojson.")
        with open('path_to_your_geojson/locations.geojson', 'r') as file:
            geojson_data = json.load(file)
        logger.info("Locations fetched successfully.")
        return JSONResponse(content=geojson_data)
    except Exception as e:
        logger.error(f"Error fetching locations: {str(e)}")
        return JSONResponse(content={"error": "Error fetching locations."}, status_code=500)


@app.get("/", response_class=HTMLResponse)
async def read_root():
    try:
        logger.info("Generating the map with GTFS data.")
        static_routes_data = gtfs.fetch_static_routes()
        combined_map = gtfs.create_combined_map(gtfs.vehicles, static_routes_data, gtfs.durham_center)
        combined_map_html = combined_map.get_root().render()
        logger.info("Map generated successfully.")
        return HTMLResponse(content=combined_map_html, status_code=200)
    except Exception as e:
        logger.error(f"Error generating map: {str(e)}")
        return HTMLResponse(content=f"<h1>Error generating map: {str(e)}</h1>", status_code=500)

# New endpoint to get map based on source and destination
@app.post("/get_map")
async def get_map(request: Request):
    try:
        logging.info("Received GET /get_map request")
        data = await request.json()
        source = data["source"]
        destination = data["destination"]

        # Generate the map using Folium
        logging.info("Generating map...")



        static_routes_data = gtfs.fetch_static_routes()
        combined_map = gtfs.create_combined_map(
            gtfs.vehicles, static_routes_data, gtfs.durham_center
        )
        

        # Return the map HTML
        logging.info("Returning map HTML...")
        return HTMLResponse(content=combined_map._repr_html_(), status_code=200)
    except Exception as e:
        logging.error(f"Error generating map: {e}")
        return HTMLResponse(content=f"<h1>Error generating map: {str(e)}</h1>", status_code=500)