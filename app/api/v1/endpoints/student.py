from fastapi import APIRouter, Request, Form, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from app.db.mongodb import get_database
from app.utils.excel_utils import parse_exam_questions
import json
import os
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

from app.core.sockets import active_connections
from app.api.v1.endpoints.administrator import broadcast_admin_stats

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    db = await get_database()
    mobile: str | None = None
    try:
        # First message must be a join request containing the student's mobile number
        try:
            join_msg = await websocket.receive_json()
        except:
            await websocket.close(code=1008)
            return

        if join_msg.get("type") != "join" or "mobile" not in join_msg:
            await websocket.close(code=1008)
            return
            
        mobile = join_msg["mobile"]
        
        # Close any existing connection for this mobile to avoid "stale" offline status
        if mobile in active_connections:
            try:
                await active_connections[mobile].close(code=1000, reason="New connection established")
            except:
                pass
                
        active_connections[mobile] = websocket
        await broadcast_admin_stats(mobile=mobile, is_online=True)
        
        # Send any previously saved state (answers and remaining timer) to the client
        student = await db["students"].find_one({"mobile": mobile})
        if student:
            await websocket.send_json({
                "type": "state",
                "answers": student.get("answers", {}),
                "remaining_seconds": student.get("remaining_seconds")
            })
        # Main loop – handle incoming messages
        while True:
            msg = await websocket.receive_json()
            msg_type = msg.get("type")
            # Check if student is still active before allowing updates
            student_check = await db["students"].find_one({"mobile": mobile}, {"status": 1})
            is_active = student_check and student_check.get("status") == "active"

            if msg_type == "answer" and is_active:
                qid = msg.get("question_id")
                ans = msg.get("answer")
                if qid and ans is not None:
                    await db["students"].update_one(
                        {"mobile": mobile},
                        {"$set": {f"answers.{qid}": ans}},
                        upsert=True,
                    )
            elif msg_type == "backup" and is_active:
                answers = msg.get("answers", {})
                remaining = msg.get("remaining_seconds")
                update_doc: dict = {}
                if answers:
                    update_doc["answers"] = answers
                if remaining is not None:
                    update_doc["remaining_seconds"] = remaining
                if update_doc:
                    await db["students"].update_one(
                        {"mobile": mobile},
                        {"$set": update_doc},
                        upsert=True,
                    )
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        if mobile and mobile in active_connections:
            del active_connections[mobile]
        await broadcast_admin_stats(mobile=mobile, is_online=False)
    finally:
        try:
            await websocket.close()
        except:
            pass



CONFIG_PATH = "app/core/portal_config.json"
EXCEL_PATH = "app/Questions/exam_questions.xlsx"

def get_portal_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

@router.get("/", response_class=HTMLResponse)
async def student_login_page(request: Request):
    config = get_portal_config()
    return templates.TemplateResponse("student/login.html", {
        "request": request,
        "exam_name": config.get("exam_name"),
        "show_animations": config.get("show_login_animations", True),
        "config": config
    })

@router.post("/register")
async def register_student(
    request: Request,
    name: str = Form(...),
    parent_name: str = Form(...),
    college: str = Form(...),
    mobile: str = Form(...),
    stream: str = Form(...),
    address: str = Form(...)
):
    db = await get_database()
    student_col = db["students"]
    
    # Check if student already exists
    existing = await student_col.find_one({"mobile": mobile})
    if existing:
        # Update existing student if needed (optional, but good for data consistency)
        await student_col.update_one(
            {"mobile": mobile},
            {"$set": {
                "parent_name": parent_name, 
                "college": college, 
                "name": name,
                "stream": stream,
                "address": address
            }}
        )
    else:
        await student_col.insert_one({
            "name": name,
            "parent_name": parent_name,
            "college": college,
            "mobile": mobile,
            "stream": stream,
            "address": address,
            "created_at": datetime.now(),
            "status": "active",
            "answers": {}
        })
    
    response = RedirectResponse(url="/student/instructions", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie("student_mobile", mobile)
    return response

@router.get("/instructions", response_class=HTMLResponse)
async def instructions_page(request: Request):
    mobile = request.cookies.get("student_mobile")
    if not mobile:
        return RedirectResponse(url="/student/")
        
    db = await get_database()
    student = await db["students"].find_one({"mobile": mobile})
    if student and student.get("status") == "completed":
        return RedirectResponse(url="/student/results")
        
    config = get_portal_config()
    exam_data = parse_exam_questions(EXCEL_PATH)
    
    response = templates.TemplateResponse("student/instructions.html", {
        "request": request,
        "config": config,
        "student": student,
        "exam_stats": {
            "total_questions": exam_data["total_questions"],
            "sections": len(exam_data["sections"]),
            "section_names": [s["name"] for s in exam_data["sections"]]
        }
    })
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@router.get("/exam", response_class=HTMLResponse)
async def exam_page(request: Request):
    mobile = request.cookies.get("student_mobile")
    if not mobile:
        return RedirectResponse(url="/student/")
        
    db = await get_database()
    student = await db["students"].find_one({"mobile": mobile})
    if not student:
        return RedirectResponse(url="/student/")
    
    if student.get("status") == "completed":
        return RedirectResponse(url="/student/results")
        
    config = get_portal_config()
    exam_data = parse_exam_questions(EXCEL_PATH)
    
    response = templates.TemplateResponse("student/exam.html", {
        "request": request,
        "config": config,
        "student": student,
        "sections": exam_data["sections"],
        "answers": student.get("answers", {}),
        "remaining_seconds": student.get("remaining_seconds", config.get("total_time_minutes", 60) * 60)
    })
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@router.post("/save-answer")
async def save_answer(request: Request):
    mobile = request.cookies.get("student_mobile")
    if not mobile:
        return JSONResponse({"status": "error", "message": "Not authenticated"}, status_code=401)
        
    data = await request.json()
    question_id = data.get("question_id")
    answer = data.get("answer")
    
    db = await get_database()
    student = await db["students"].find_one({"mobile": mobile})
    if not student or student.get("status") != "active":
        return JSONResponse({"status": "error", "message": "Exam already submitted or inactive"}, status_code=403)
        
    await db["students"].update_one(
        {"mobile": mobile},
        {"$set": {f"answers.{question_id}": answer}}
    )
    
    return {"status": "success"}

@router.post("/finish-exam")
async def finish_exam_api(request: Request):
    mobile = request.cookies.get("student_mobile")
    if not mobile:
        return JSONResponse({"status": "error", "message": "Not authenticated"}, status_code=401)
    
    db = await get_database()
    student = await db["students"].find_one({"mobile": mobile})
    if not student or student.get("status") == "completed":
        return JSONResponse({"status": "error", "message": "Exam already submitted"}, status_code=400)

    await db["students"].update_one(
        {"mobile": mobile},
        {"$set": {"status": "completed", "completed_at": datetime.now()}}
    )
    await broadcast_admin_stats(mobile=mobile, is_online=False)
    return {"status": "success"}

@router.get("/results", response_class=HTMLResponse)
async def results_page(request: Request):
    mobile = request.cookies.get("student_mobile")
    if not mobile:
        return RedirectResponse(url="/student/")
        
    db = await get_database()
    student = await db["students"].find_one({"mobile": mobile})
    
    if not student:
        response = RedirectResponse(url="/student/")
        response.delete_cookie("student_mobile")
        return response
        
    exam_data = parse_exam_questions(EXCEL_PATH)
    
    # Calculate results
    results = []
    total_correct = 0
    total_answered = 0
    
    for section in exam_data["sections"]:
        correct_in_section = 0
        for q in section["questions"]:
            student_ans = student.get("answers", {}).get(q["id"])
            if student_ans:
                total_answered += 1
                if student_ans == q["correct"]:
                    correct_in_section += 1
                    total_correct += 1
        
        results.append({
            "name": section["name"],
            "correct": correct_in_section,
            "total": section["count"],
            "percentage": round((correct_in_section / section["count"]) * 100, 2) if section["count"] > 0 else 0
        })
        
    total_incorrect = total_answered - total_correct
    total_unattended = exam_data["total_questions"] - total_answered
    overall_percent = round((total_correct / exam_data["total_questions"]) * 100, 2) if exam_data["total_questions"] > 0 else 0
    
    from app.api.v1.endpoints.administrator import get_portal_config
    config = get_portal_config()
    
    return templates.TemplateResponse("student/results.html", {
        "request": request,
        "student": student,
        "results": results,
        "overall_percent": overall_percent,
        "total_correct": total_correct,
        "total_incorrect": total_incorrect,
        "total_unattended": total_unattended,
        "total_questions": exam_data["total_questions"],
        "config": config
    })
