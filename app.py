from fastapi import FastAPI, File, UploadFile
import shutil, os, uuid
from validate import validate_document

app = FastAPI()

@app.post("/validate/")
async def validate(file: UploadFile = File(...)):
    # Save uploaded file temporarily
    temp_filename = f"/tmp/{uuid.uuid4()}_{file.filename}"
    with open(temp_filename, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Run validation
    result = validate_document(temp_filename)

    # Cleanup
    os.remove(temp_filename)

    return result

@app.get("/")
def root():
    return {"status": "ID Validator API running"}
