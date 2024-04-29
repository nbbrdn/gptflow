from fastapi import FastAPI, Query
from datetime import datetime, timezone, timedelta

app = FastAPI()


@app.get("/time/")
async def get_local_time(offset: int = Query(..., ge=-12, le=14)):
    tz = timezone(timedelta(hours=offset))
    local_time = datetime.now(tz)
    return {"timezone": offset, "current_time": local_time}
