from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.generator import generate_terraform
from app.models import InfraRequest, InfraResponse
from app.parser import parse_request
from app.validator import validate_terraform

app=FastAPI(title="Natural Language to Infrastructure Generator",version="1.0.0")
static=Path(__file__).parent/"static"; app.mount("/static",StaticFiles(directory=static),name="static")
@app.get("/",include_in_schema=False)
def home(): return FileResponse(static/"index.html")
@app.get("/health")
def health(): return {"status":"ok"}
@app.post("/generate",response_model=InfraResponse)
def generate(request:InfraRequest):
    spec=parse_request(request.request); code=generate_terraform(spec); validation=validate_terraform(code)
    return InfraResponse(specification=spec,terraform=code,validation=validation)
