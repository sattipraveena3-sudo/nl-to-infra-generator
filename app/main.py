import base64,io,zipfile
from pathlib import Path
from fastapi import FastAPI,HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.generator import generate_project
from app.models import InfraRequest,InfraResponse
from app.parser import parse_request
from app.validator import correct_project,validate_project

app=FastAPI(title="Natural Language to Infrastructure Generator",version="2.0.0");static=Path(__file__).parent/"static";app.mount("/static",StaticFiles(directory=static),name="static")
def bundle(files):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,"w",zipfile.ZIP_DEFLATED) as z:
        for name,content in files.items():z.writestr(name,content)
    return base64.b64encode(stream.getvalue()).decode()
@app.get("/",include_in_schema=False)
def home():return FileResponse(static/"index.html")
@app.get("/health")
def health():
    import shutil
    return {"status":"ok","terraform_available":bool(shutil.which("terraform")),"supported_resources":["s3","lambda","dynamodb","iam","s3_notification"]}
@app.post("/generate",response_model=InfraResponse)
def generate(request:InfraRequest):
    try:spec,parser_used=parse_request(request.request,request.project_name,request.parser)
    except Exception as e:raise HTTPException(503,f"selected parser unavailable: {e}") from e
    files=generate_project(spec);validation=validate_project(files,request.run_plan)
    if not validation.valid:
        fixed,summary=correct_project(files,validation)
        if fixed!=files:
            files=fixed;second=validate_project(files,request.run_plan);second.corrected=True;second.correction_summary=summary;validation=second
    return InfraResponse(specification=spec,parser_used=parser_used,files=files,validation=validation,bundle_base64=bundle(files))
