from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from .database import engine, Base, get_db
from .models import Course, User, AppConfig, SavedCourse, CourseFeedback
from .auth import send_otp, verify_otp, get_resend_api_key
from .scraper import scrape_catalog, fetch_details
import os

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, db: Session = Depends(get_db)):
    # Check if user is logged in
    user = None
    token = request.cookies.get("access_token")
    if token:
        try:
            from jose import jwt
            from .auth import SECRET_KEY, ALGORITHM
            scheme, _, param = token.partition(" ")
            payload = jwt.decode(param, SECRET_KEY, algorithms=[ALGORITHM])
            email = payload.get("sub")
            user = db.query(User).filter(User.email == email).first()
        except Exception:
            pass
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

@app.get("/admin", response_class=HTMLResponse)
async def read_admin(request: Request, db: Session = Depends(get_db)):
    # Check if user is admin
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/", status_code=303)
    
    try:
        from jose import jwt
        from .auth import SECRET_KEY, ALGORITHM
        scheme, _, param = token.partition(" ")
        payload = jwt.decode(param, SECRET_KEY, algorithms=[ALGORITHM])
        is_admin = payload.get("admin", False)
        if not is_admin:
            return RedirectResponse(url="/", status_code=303)
    except Exception:
        return RedirectResponse(url="/", status_code=303)
    
    return templates.TemplateResponse("admin.html", {"request": request})

@app.get("/my-courses", response_class=HTMLResponse)
async def my_courses(request: Request, db: Session = Depends(get_db)):
    # Require login
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/", status_code=303)
    
    try:
        from jose import jwt
        from .auth import SECRET_KEY, ALGORITHM
        scheme, _, param = token.partition(" ")
        payload = jwt.decode(param, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return RedirectResponse(url="/", status_code=303)
    except Exception:
        return RedirectResponse(url="/", status_code=303)
    
    # Get saved courses
    saved_courses = db.query(SavedCourse).filter(SavedCourse.user_id == user.id).all()
    
    # Get upvoted courses (positive feedback)
    upvoted_courses = db.query(CourseFeedback).filter(
        CourseFeedback.user_id == user.id,
        CourseFeedback.is_positive == True
    ).all()
    
    return templates.TemplateResponse("my_courses.html", {
        "request": request,
        "user": user,
        "saved_courses": saved_courses,
        "upvoted_courses": upvoted_courses
    })

from .embeddings import generate_query_embedding

@app.get("/search")
def search_courses(request: Request, q: str, db: Session = Depends(get_db)):
    if not q:
        return []
    
    # Generate query embedding
    query_emb = generate_query_embedding(q)
    
    # Vector search using pgvector l2_distance or cosine_distance
    # Nomic embeddings are normalized? If so, cosine is dot product or l2. 
    # Usually cosine distance <=> 1 - cosine similarity. 
    # pgvector operator <-> is L2 distance, <=> is cosine distance, <#> is negative inner product.
    # Recommended for Nomic: Cosine similarity. So use <=> (cosine distance) and order by it ASC.
    
    results = db.query(Course).order_by(Course.embedding.cosine_distance(query_emb)).limit(20).all()
    
    return templates.TemplateResponse("search_results.html", {"request": request, "results": results})

from fastapi.responses import HTMLResponse, RedirectResponse

# ... (imports)

@app.post("/auth/login")
def login(request: Request, email: str = Form(...), db: Session = Depends(get_db)):
    # Check admin or nyu.edu
    # Assuming send_otp handles the check, but let's be safe or rely on send_otp return
    result = send_otp(email, db)
    if "error" in result:
        return templates.TemplateResponse("partials/error.html", {"request": request, "message": result["error"]})
    return templates.TemplateResponse("partials/success.html", {"request": request, "message": result["message"]})

@app.post("/auth/verify")
def verify(request: Request, email: str = Form(...), otp: str = Form(...), db: Session = Depends(get_db)):
    token = verify_otp(email, otp, db)
    if not token:
        # returns 200 with error template for HTMX to swap
        return templates.TemplateResponse("partials/error.html", {"request": request, "message": "Invalid or expired OTP"})
    
    # HTMX redirect via header or just standard redirect if target is body?
    # For full page reload/redirect:
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True)
    return response

@app.get("/auth/logout")
def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key="access_token")
    return response

@app.post("/courses/{course_id}/save")
def save_course(course_id: str, request: Request, db: Session = Depends(get_db)):
    # Auth check: naive cookie check or dependency
    token = request.cookies.get("access_token")
    if not token:
         return templates.TemplateResponse("partials/error.html", {"request": request, "message": "Please login to save courses"})
    
    # decode token (simple check, prod needs full verification)
    try:
        from jose import jwt
        from .auth import SECRET_KEY, ALGORITHM
        scheme, _, param = token.partition(" ")
        payload = jwt.decode(param, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise Exception("User not found")
    except Exception:
        return templates.TemplateResponse("partials/error.html", {"request": request, "message": "Invalid session, please login again"})
        
    # Check if already saved
    from .models import SavedCourse
    existing = db.query(SavedCourse).filter(SavedCourse.user_id == user.id, SavedCourse.course_id == course_id).first()
    if existing:
        db.delete(existing)
        db.commit()
        msg = "Course unsaved"
        icon_fill = "none"
    else:
        new_save = SavedCourse(user_id=user.id, course_id=course_id)
        db.add(new_save)
        db.commit()
        msg = "Course saved"
        icon_fill = "currentColor"
        
    # Return button state (HTMX swap outerHTML of the button)
    return templates.TemplateResponse("partials/save_button.html", {
        "request": request, 
        "course_id": course_id, 
        "saved": not existing
    })

@app.post("/courses/{course_id}/upvote")
def upvote_course(course_id: str, request: Request, db: Session = Depends(get_db)):
    # Auth check
    token = request.cookies.get("access_token")
    if not token:
        return templates.TemplateResponse("partials/error.html", {"request": request, "message": "Please login to upvote courses"})
    
    try:
        from jose import jwt
        from .auth import SECRET_KEY, ALGORITHM
        scheme, _, param = token.partition(" ")
        payload = jwt.decode(param, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise Exception("User not found")
    except Exception:
        return templates.TemplateResponse("partials/error.html", {"request": request, "message": "Invalid session, please login again"})
    
    # Toggle upvote using CourseFeedback model
    from .models import CourseFeedback
    existing = db.query(CourseFeedback).filter(
        CourseFeedback.user_id == user.id, 
        CourseFeedback.course_id == course_id
    ).first()
    
    if existing:
        db.delete(existing)
        db.commit()
        upvoted = False
    else:
        new_feedback = CourseFeedback(user_id=user.id, course_id=course_id, is_positive=True)
        db.add(new_feedback)
        db.commit()
        upvoted = True
    
    return templates.TemplateResponse("partials/upvote_button.html", {
        "request": request, 
        "course_id": course_id, 
        "upvoted": upvoted
    })

@app.post("/admin/config")
def set_config(key: str = Form(...), value: str = Form(...), db: Session = Depends(get_db)):
    # Check if admin (TODO: add auth dependency)
    conf = db.query(AppConfig).filter(AppConfig.key == key).first()
    if not conf:
        conf = AppConfig(key=key, value=value)
        db.add(conf)
    else:
        conf.value = value
    db.commit()
    return {"status": "updated", "key": key}

@app.get("/admin/users")
def list_users(db: Session = Depends(get_db)):
    # Check if admin
    users = db.query(User).all()
    return [{"email": u.email, "is_verified": u.is_verified, "is_admin": u.is_admin} for u in users]

@app.get("/admin/stats")
def admin_stats(db: Session = Depends(get_db)):
    total_courses = db.query(Course).count()
    total_users = db.query(User).count()
    courses_with_embeddings = db.query(Course).filter(Course.embedding.is_not(None)).count()
    return {
        "total_courses": total_courses,
        "total_users": total_users,
        "courses_with_embeddings": courses_with_embeddings
    }

@app.get("/admin/stats-html", response_class=HTMLResponse)
def admin_stats_html(request: Request, db: Session = Depends(get_db)):
    total_courses = db.query(Course).count()
    total_users = db.query(User).count()
    courses_with_embeddings = db.query(Course).filter(Course.embedding.is_not(None)).count()
    return templates.TemplateResponse("partials/admin_stats.html", {
        "request": request,
        "total_courses": total_courses,
        "total_users": total_users,
        "courses_with_embeddings": courses_with_embeddings
    })

@app.get("/admin/users-html", response_class=HTMLResponse)
def admin_users_html(request: Request, db: Session = Depends(get_db)):
    users = db.query(User).all()
    return templates.TemplateResponse("partials/admin_users.html", {
        "request": request,
        "users": users
    })

@app.get("/course/{course_id}", response_class=HTMLResponse)
def get_course_detail(course_id: str, request: Request, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Check if user has saved/upvoted this course
    is_saved = False
    is_upvoted = False
    token = request.cookies.get("access_token")
    if token:
        try:
            from jose import jwt
            from .auth import SECRET_KEY, ALGORITHM
            scheme, _, param = token.partition(" ")
            payload = jwt.decode(param, SECRET_KEY, algorithms=[ALGORITHM])
            email = payload.get("sub")
            user = db.query(User).filter(User.email == email).first()
            if user:
                is_saved = db.query(SavedCourse).filter(
                    SavedCourse.user_id == user.id, 
                    SavedCourse.course_id == course_id
                ).first() is not None
                is_upvoted = db.query(CourseFeedback).filter(
                    CourseFeedback.user_id == user.id,
                    CourseFeedback.course_id == course_id,
                    CourseFeedback.is_positive == True
                ).first() is not None
        except Exception:
            pass
    
    return templates.TemplateResponse("course_detail.html", {
        "request": request, 
        "course": course,
        "is_saved": is_saved,
        "is_upvoted": is_upvoted
    })

@app.post("/admin/scrape")
async def trigger_scrape(db: Session = Depends(get_db)):
    return await scrape_catalog(db)

@app.get("/api/classes/{course_id}")
async def get_live_classes(course_id: str, request: Request, db: Session = Depends(get_db)):
    """Fetch live class sections from NYU Class Search API."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return templates.TemplateResponse("partials/error.html", {"request": request, "message": "Course not found"})
    
    from .class_search import fetch_class_sections_multi_term, format_class_for_display
    
    result = await fetch_class_sections_multi_term(course.course_code)
    
    if result.get("error"):
        return templates.TemplateResponse("partials/classes_error.html", {
            "request": request, 
            "message": result["error"]
        })
    
    # Check if no classes found
    if result.get("count", 0) == 0:
        return templates.TemplateResponse("partials/classes_list.html", {
            "request": request,
            "classes": [],
            "count": 0,
            "message": result.get("message", "No class sections found."),
            "course_code": course.course_code
        })
    
    classes = [format_class_for_display(c) for c in result.get("classes", [])]
    
    return templates.TemplateResponse("partials/classes_list.html", {
        "request": request,
        "classes": classes,
        "count": len(classes),
        "term_name": result.get("term_name", ""),
        "course_code": course.course_code
    })
