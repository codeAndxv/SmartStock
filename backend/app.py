"""FastAPI backend for SmartStock."""

import json
from dataclasses import asdict
from datetime import date

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.core.scan_limit_up import scan_and_predict, scan_and_predict_with_progress

app = FastAPI(title="SmartStock API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET"],
)


@app.get("/api/limit-up")
def get_limit_up():
    """Return today's limit-up stocks with predictions."""
    try:
        predictions = scan_and_predict()
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {
        "date": date.today().isoformat(),
        "count": len(predictions),
        "predictions": [asdict(p) for p in predictions],
    }


@app.get("/api/limit-up/stream")
def stream_limit_up():
    """Stream limit-up scan progress via SSE, then send final result."""

    def event_stream():
        gen = scan_and_predict_with_progress()
        try:
            while True:
                current, total, code, name = next(gen)
                data = json.dumps({
                    "type": "progress",
                    "current": current,
                    "total": total,
                    "code": code,
                    "name": name,
                }, ensure_ascii=False)
                yield f"data: {data}\n\n"
        except StopIteration as e:
            predictions = e.value if e.value else []
            data = json.dumps({
                "type": "done",
                "date": date.today().isoformat(),
                "count": len(predictions),
                "predictions": [asdict(p) for p in predictions],
            }, ensure_ascii=False)
            yield f"data: {data}\n\n"
        except ValueError as e:
            data = json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False)
            yield f"data: {data}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )