# Monkeypatch protobuf to bypass call-stack checks in Python 3.13+ / 3.14+
try:
    from google._upb import _message as _upb_message
    _upb_message.Message._CheckCalledFromGeneratedFile = lambda *args, **kwargs: None
except Exception:
    pass

try:
    from google.protobuf.pyext import _message as _cpp_message
    _cpp_message.Message._CheckCalledFromGeneratedFile = lambda *args, **kwargs: None
except Exception:
    pass

import os
import shutil
import tempfile
import threading
import queue
import json
import asyncio
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from langchain_core.callbacks import BaseCallbackHandler
import agent

# QueueCallbackHandler forwards LangChain execution events to a thread-safe Queue for SSE streaming
class QueueCallbackHandler(BaseCallbackHandler):
    def __init__(self, q: queue.Queue):
        self.q = q
        self.logs = []

    def on_llm_start(self, serialized, prompts, **kwargs):
        log = "LLM starting generation..."
        self.logs.append(log)
        self.q.put(("log", log))
        
    def on_tool_start(self, serialized, input_str, **kwargs):
        tool_name = serialized.get("name", "Unknown Tool")
        log = f"Executing tool `{tool_name}` with input: `{input_str}`"
        self.logs.append(log)
        self.q.put(("log", log))
        
    def on_tool_end(self, output, **kwargs):
        serialized_output = str(output)
        if isinstance(output, tuple) and len(output) > 0:
            serialized_output = str(output[0])
            
        if len(serialized_output) > 500:
            serialized_output = serialized_output[:500] + "... (truncated)"
            
        log = f"Tool finished! Result:\n```\n{serialized_output}\n```"
        self.logs.append(log)
        self.q.put(("log", log))
        
    def on_llm_end(self, response, **kwargs):
        log = "LLM finished generating."
        self.logs.append(log)
        self.q.put(("log", log))

# Pydantic models for incoming chat queries
class ChatMessage(BaseModel):
    role: str
    content: str
    sources: Optional[List[Dict[str, Any]]] = None
    thinking: Optional[List[str]] = None

class QueryRequest(BaseModel):
    prompt: str
    history: Optional[List[ChatMessage]] = None

class DeleteRequest(BaseModel):
    filename: str

app = FastAPI(title="Search Agent Backend")

# Enable CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi import Request
from fastapi.responses import JSONResponse
import traceback

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print("LOGGING UNHANDLED EXCEPTION:")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "detail": str(exc)},
    )

# Serve the static single-page application (index.html)
@app.get("/")
async def get_index():
    index_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(index_path)

# Healthcheck endpoint (required for cloud hosting/health probes)
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

# Retrieve list of all unique indexed document names
@app.get("/documents")
async def get_documents():
    try:
        docs = agent.get_indexed_documents()
        return {"documents": docs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Clear all items from the Chroma vector collection
@app.post("/clear")
async def clear_database():
    try:
        agent.clear_vector_store()
        return {"message": "Database cleared!"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# Delete a specific document by filename from Chroma vector collection
@app.post("/delete")
async def delete_document(req: DeleteRequest):
    try:
        success = agent.delete_document(req.filename)
        if success:
            return {"message": f"Document '{req.filename}' deleted successfully!"}
        else:
            raise HTTPException(status_code=404, detail=f"Document '{req.filename}' not found.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# Index file uploads
@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pdf", ".docx", ".txt", ".md"]:
        raise HTTPException(status_code=400, detail=f"Unsupported file extension: {ext}")
        
    try:
        # Write to a temporary file, then parse and chunk
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
            
        chunks = agent.process_document(tmp_path, original_filename=file.filename)
        return {"filename": file.filename, "chunks": chunks}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.remove(tmp_path)

# Query agent with real-time log streaming using Server-Sent Events (SSE)
@app.post("/query")
async def query_agent(req: QueryRequest):
    q = queue.Queue()
    callback = QueueCallbackHandler(q)
    
    # Map chat history format to simple dict list
    history_dicts = []
    if req.history:
        for msg in req.history:
            history_dicts.append({
                "role": msg.role,
                "content": msg.content
            })
            
    # Executing the agent in a daemon thread so it runs in parallel with the SSE generator
    def run_agent_thread():
        try:
            res = agent.ask_agent(req.prompt, chat_history=history_dicts, callbacks=[callback])
            q.put(("result", res))
        except Exception as e:
            q.put(("error", str(e)))
        finally:
            q.put(("done", None))
            
    thread = threading.Thread(target=run_agent_thread, daemon=True)
    thread.start()
    
    # Generator retrieves logs/results from queue and yields as SSE lines
    async def sse_generator():
        loop = asyncio.get_running_loop()
        while True:
            try:
                # Retrieve from sync queue without blocking event loop
                event_type, data = await loop.run_in_executor(None, q.get)
            except Exception:
                break
                
            if event_type == "done":
                break
            elif event_type == "log":
                yield f"data: {json.dumps({'type': 'log', 'data': data})}\n\n"
            elif event_type == "result":
                yield f"data: {json.dumps({'type': 'result', 'data': data})}\n\n"
            elif event_type == "error":
                yield f"data: {json.dumps({'type': 'error', 'data': data})}\n\n"
                
    return StreamingResponse(sse_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8501))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
