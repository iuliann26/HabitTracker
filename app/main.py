from fastapi import FastAPI, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.db import engine, Base, get_db
from app import models
from datetime import date, datetime
from fastapi.staticfiles import StaticFiles

models.Base.metadata.create_all(bind=engine)
app = FastAPI(title="PersonalOS")
templates = Jinja2Templates(directory="app/templates")

def get_or_create_today_log(db: Session) -> models.DailyLog:
    today = date.today()
    log = db.query(models.DailyLog).filter(models.DailyLog.log_date == today).first()
    if not log:
        log = models.DailyLog(log_date=today)
        db.add(log)
        db.commit()
        db.refresh(log)
    return log

@app.get("/dashboard")
def render_dashboard(request: Request, db: Session = Depends(get_db)):
    profile = db.query(models.UserProfile).first()
    if not profile:
        profile = models.UserProfile()
        db.add(profile)
        db.commit()
        db.refresh(profile)

    today_log = get_or_create_today_log(db)

    # 1. Calcul dinamic pentru Scorul Zilei
    core_habits = [
        today_log.prog_completed,
        today_log.plc_completed,
        today_log.elec_completed,
        today_log.project_completed,
        today_log.gym_completed,
        today_log.review_completed
    ]
    completed_count = sum(1 for h in core_habits if h)
    daily_score_pct = int((completed_count / 6) * 100)

    # 2. Calcul Progress Bar pentru XP (Cât mai ai până la nivelul următor)
    current_level_base_xp = int(100 * ((profile.level - 1) ** 1.5)) if profile.level > 1 else 0
    next_level_xp = int(100 * (profile.level ** 1.5))
    xp_needed = next_level_xp - current_level_base_xp
    xp_earned = profile.xp_current - current_level_base_xp
    xp_progress_pct = int((xp_earned / xp_needed) * 100) if xp_needed > 0 else 0

    # Plan fumat
    days_passed = (date.today() - profile.smoking_start_date).days
    smoke_target = max(0, 15 - (days_passed // 7))

    # Nutriție
    today_meals = db.query(models.MealLog).filter(models.MealLog.log_date == date.today()).all()
    total_calories = sum(meal.calories for meal in today_meals)

    # Finanțe (Grafic)
    past_logs = db.query(models.DailyLog).order_by(models.DailyLog.log_date.desc()).limit(7).all()
    past_logs.reverse()
    chart_labels = [log.log_date.strftime("%d-%m") for log in past_logs]
    chart_data = [log.expenses_total for log in past_logs]
    budget_zilnic = profile.monthly_budget / 30

    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request, 
            "profile": profile, 
            "log": today_log, 
            "smoke_target": smoke_target,
            "budget_zilnic": budget_zilnic,
            "chart_labels": chart_labels,
            "chart_data": chart_data,
            "today_meals": today_meals,
            "total_calories": total_calories,
            "daily_score_pct": daily_score_pct,
            "xp_progress_pct": xp_progress_pct,
            "next_level_xp": next_level_xp,
            "getattr": getattr,
            "date": date
        }
    )

@app.post("/toggle-habit/{habit_name}")
def toggle_habit(habit_name: str, db: Session = Depends(get_db)):
    log = get_or_create_today_log(db)
    profile = db.query(models.UserProfile).first()
    
    current_state = getattr(log, habit_name)
    setattr(log, habit_name, not current_state)
    
    # REZOLVARE PUNCT 1: Adăugare XP la bifare, scădere XP la debifare
    if current_state:  # Era True, devine False (Debifare)
        profile.xp_current = max(0, profile.xp_current - 15)
        while profile.level > 1 and profile.xp_current < int(100 * ((profile.level - 1) ** 1.5)):
            profile.level -= 1
    else:  # Era False, devine True (Bifare)
        profile.xp_current += 15
        while profile.xp_current >= int(100 * (profile.level ** 1.5)):
            profile.level += 1
            
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=303)

@app.post("/update-cigarettes")
def update_cigarettes(count: int = Form(...), db: Session = Depends(get_db)):
    log = get_or_create_today_log(db)
    log.cigarettes_count = count
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=303)

# REZOLVARE PUNCT 3: Adăugare masă cu oră automată
@app.post("/add-meal")
def add_meal(meal_name: str = Form(...), calories: int = Form(...), db: Session = Depends(get_db)):
    today = date.today()
    # Calculăm caloriile înainte de a adăuga noua masă
    today_meals = db.query(models.MealLog).filter(models.MealLog.log_date == today).all()
    total_before = sum(meal.calories for meal in today_meals)
    
    current_time = datetime.now().strftime("%H:%M")
    new_drop = models.MealLog(
        log_date=today,
        meal_time=current_time,
        meal_name=meal_name,
        calories=calories
    )
    db.add(new_drop)
    
    # BONUS GAMIFICATION: Verificăm dacă prin adăugarea acestei mese ai atins 3000 kcal
    total_after = total_before + calories
    if total_before < 3000 and total_after >= 3000:
        profile = db.query(models.UserProfile).first()
        profile.xp_current += 50  # BONUS 50 XP pentru atingerea targetului de bulk
        while profile.xp_current >= int(100 * (profile.level ** 1.5)):
            profile.level += 1
            
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=303)

@app.post("/add-expense")
def add_expense(amount: float = Form(...), db: Session = Depends(get_db)):
    log = get_or_create_today_log(db)
    log.expenses_total += amount
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=303)
@app.get("/stats")
def render_stats(request: Request, db: Session = Depends(get_db)):
    logs = db.query(models.DailyLog).all()
    profile = db.query(models.UserProfile).first()
    
    if not logs:
        return {"message": "Nu există suficiente date pentru statistici."}
        
    total_days = len(logs)
    
    # 1. Calcul cheltuieli
    total_spent = sum(log.expenses_total for log in logs)
    
    # 2. Calcul fumat
    total_cigarettes = sum(log.cigarettes_count for log in logs)
    avg_cigarettes = total_cigarettes / total_days
    
    # 3. Disciplină Core Habits (Câte bife din totalul posibil au fost puse)
    total_possible_habits = total_days * 6
    completed_habits = 0
    for log in logs:
        if log.prog_completed: completed_habits += 1
        if log.plc_completed: completed_habits += 1
        if log.elec_completed: completed_habits += 1
        if log.project_completed: completed_habits += 1
        if log.gym_completed: completed_habits += 1
        if log.review_completed: completed_habits += 1
        
    discipline_score = (completed_habits / total_possible_habits) * 100 if total_possible_habits > 0 else 0

    return templates.TemplateResponse(
        "stats.html",
        {
            "request": request,
            "profile": profile,
            "total_days": total_days,
            "total_spent": total_spent,
            "avg_cigarettes": round(avg_cigarettes, 1),
            "discipline_score": round(discipline_score, 1)
        }
    )