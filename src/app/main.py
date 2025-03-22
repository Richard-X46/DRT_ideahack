from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI()

# Serve static files from 'src/app/static'
app.mount("/static", StaticFiles(directory="src/app/static"), name="static")

# Serve the 'index.html' file from 'src/app/templates'
@app.get("/", response_class=HTMLResponse)
async def read_root():
    # Ensure this path points to the correct location of 'index.html'
    index_path = os.path.join("src", "app", "static","templates", "index.html")
    
    try:
        with open(index_path, "r", encoding="utf-8") as file:
            return HTMLResponse(content=file.read(), status_code=200)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Error: index.html not found</h1>", status_code=404)
