from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
import math

app = FastAPI(title="IronFit Gym Management System")

plans = [
    {"id": 1, "name": "Basic",    "duration_months": 1,  "price": 1000, "includes_classes": False, "includes_trainer": False},
    {"id": 2, "name": "Standard", "duration_months": 3,  "price": 2500, "includes_classes": True,  "includes_trainer": False},
    {"id": 3, "name": "Premium",  "duration_months": 6,  "price": 4500, "includes_classes": True,  "includes_trainer": True},
    {"id": 4, "name": "Elite",    "duration_months": 12, "price": 8000, "includes_classes": True,  "includes_trainer": True},
    {"id": 5, "name": "Trial",    "duration_months": 1,  "price": 500,  "includes_classes": False, "includes_trainer": False},
]

memberships = []
membership_counter = 1 

class_bookings = []
class_counter = 1

class EnrollRequest(BaseModel):
    member_name: str = Field(..., min_length=2)
    plan_id: int = Field(..., gt=0)
    phone: str = Field(..., min_length=10)
    start_month: str = Field(..., min_length=3)
    payment_mode: str = "cash"
    referral_code: Optional[str] = "" 


class NewPlan(BaseModel):
    name: str = Field(..., min_length=2)
    duration_months: int = Field(..., gt=0)
    price: int = Field(..., gt=0)
    includes_classes: bool = False
    includes_trainer: bool = False


class ClassBookingRequest(BaseModel):
    member_name: str
    class_name: str
    class_date: str

def find_plan(plan_id: int):
    return next((p for p in plans if p["id"] == plan_id), None)


def find_membership(membership_id: int):
    return next((m for m in memberships if m["membership_id"] == membership_id), None)


def calculate_membership_fee(base_price: int, duration: int, payment_mode: str, referral: str = ""):
    fee = base_price
    discount_note = "No discount"

    if duration >= 12:
        fee *= 0.8
        discount_note = "20% Annual Discount"
    elif duration >= 6:
        fee *= 0.9
        discount_note = "10% Semi-Annual Discount"

    if payment_mode.lower() == "emi":
        fee += 200

    if referral:
        fee *= 0.95
        discount_note += " + 5% Referral Discount"

    return round(fee, 2), discount_note


def filter_plans_logic(
    data,
    includes_classes=None,
    includes_trainer=None,
    max_price=None,
    duration_months=None,
):
    result = data[:]
    if includes_classes is not None:
        result = [p for p in result if p["includes_classes"] == includes_classes]
    if includes_trainer is not None:
        result = [p for p in result if p["includes_trainer"] == includes_trainer]
    if max_price is not None:
        result = [p for p in result if p["price"] <= max_price]
    if duration_months is not None:
        result = [p for p in result if p["duration_months"] == duration_months]
    return result

@app.get("/")
def home():
    return {"message": "Welcome to IronFit Gym"}

@app.get("/plans/summary")
def get_plans_summary():
    prices = [p["price"] for p in plans]
    return {
        "total_plans": len(plans),
        "with_classes": len([p for p in plans if p["includes_classes"]]),
        "with_trainer": len([p for p in plans if p["includes_trainer"]]),
        "min_price": min(prices) if prices else 0,
        "max_price": max(prices) if prices else 0,
    }

@app.get("/plans/filter")
def filter_plans(
    includes_classes: Optional[bool] = None,
    includes_trainer: Optional[bool] = None,
    max_price: Optional[int] = None,
    duration_months: Optional[int] = None,
):
    result = filter_plans_logic(plans, includes_classes, includes_trainer, max_price, duration_months)
    return {"plans": result, "total": len(result)}

@app.get("/plans/search")
def search_plans(keyword: str = Query(..., min_length=1)):
    results = [p for p in plans if keyword.lower() in p["name"].lower()]
    if not results:
        return {"message": f"No plans found matching '{keyword}'", "total_found": 0, "results": []}
    return {"total_found": len(results), "results": results}

VALID_PLAN_SORT_FIELDS = ["price", "name", "duration_months"]

@app.get("/plans/sort")
def sort_plans(sort_by: str = "price", order: str = "asc"):
    if sort_by not in VALID_PLAN_SORT_FIELDS:
        raise HTTPException(status_code=400, detail=f"sort_by must be one of {VALID_PLAN_SORT_FIELDS}")
    if order not in ("asc", "desc"):
        raise HTTPException(status_code=400, detail="order must be 'asc' or 'desc'")

    sorted_plans = sorted(plans, key=lambda x: x[sort_by], reverse=(order == "desc"))
    return {"sort_by": sort_by, "order": order, "plans": sorted_plans}

@app.get("/plans/page")
def paginate_plans(page: int = Query(1, ge=1), limit: int = Query(2, ge=1)):
    total = len(plans)
    total_pages = math.ceil(total / limit)
    start = (page - 1) * limit
    sliced = plans[start : start + limit]
    return {
        "total": total,
        "total_pages": total_pages,
        "page": page,
        "limit": limit,
        "plans": sliced,
    }

@app.get("/plans/browse")
def browse_plans(
    keyword: Optional[str] = None,
    includes_classes: Optional[bool] = None,
    includes_trainer: Optional[bool] = None,
    max_price: Optional[int] = None,
    sort_by: str = "price",
    order: str = "asc",
    page: int = Query(1, ge=1),
    limit: int = Query(2, ge=1),
):
    results = filter_plans_logic(plans, includes_classes, includes_trainer, max_price)
    if keyword:
        results = [p for p in results if keyword.lower() in p["name"].lower()]

    results = sorted(results, key=lambda x: x.get(sort_by, 0), reverse=(order == "desc"))

    total = len(results)
    pages = math.ceil(total / limit) if total else 0
    start = (page - 1) * limit
    paginated = results[start : start + limit]

    return {
        "metadata": {
            "keyword": keyword,
            "sort_by": sort_by,
            "order": order,
            "total": total,
            "pages": pages,
            "current_page": page,
        },
        "results": paginated,
    }
@app.get("/plans")
def get_all_plans():
    prices = [p["price"] for p in plans]
    return {
        "plans": plans,
        "total": len(plans),
        "price_range": {"min": min(prices), "max": max(prices)},
    }
@app.get("/plans/{plan_id}")
def get_plan(plan_id: int):
    plan = find_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan

@app.post("/plans", status_code=201)
def add_plan(plan_in: NewPlan):
    if any(p["name"].lower() == plan_in.name.lower() for p in plans):
        raise HTTPException(status_code=400, detail="Plan name already exists")

    new_id = max(p["id"] for p in plans) + 1
    new_plan = {"id": new_id, **plan_in.dict()}
    plans.append(new_plan)
    return new_plan

@app.put("/plans/{plan_id}")
def update_plan(
    plan_id: int,
    price: Optional[int] = Query(None, gt=0),
    includes_trainer: Optional[bool] = None,
):
    plan = find_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    if price is not None:
        plan["price"] = price
    if includes_trainer is not None:
        plan["includes_trainer"] = includes_trainer

    return plan

@app.delete("/plans/{plan_id}")
def delete_plan(plan_id: int):
    plan = find_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    active_on_plan = any(
        m["plan_name"] == plan["name"] and m["status"] == "active"
        for m in memberships
    )
    if active_on_plan:
        raise HTTPException(status_code=400, detail="Cannot delete plan with active members")

    plans.remove(plan)
    return {"message": f"Plan '{plan['name']}' deleted successfully"}

@app.get("/memberships")
def get_all_memberships():
    return {"memberships": memberships, "total": len(memberships)}

@app.get("/memberships/active")
def get_active_memberships():
    active = [m for m in memberships if m["status"] == "active"]
    return {"memberships": active, "total": len(active)}

@app.get("/memberships/search")
def search_memberships(member_name: str = Query(..., min_length=1)):
    results = [m for m in memberships if member_name.lower() in m["member_name"].lower()]
    if not results:
        return {"message": f"No memberships found for '{member_name}'", "total_found": 0, "results": []}
    return {"total_found": len(results), "results": results}

VALID_MEMBERSHIP_SORT_FIELDS = ["total_fee", "duration"]

@app.get("/memberships/sort")
def sort_memberships(sort_by: str = "total_fee", order: str = "asc"):
    if sort_by not in VALID_MEMBERSHIP_SORT_FIELDS:
        raise HTTPException(status_code=400, detail=f"sort_by must be one of {VALID_MEMBERSHIP_SORT_FIELDS}")
    if order not in ("asc", "desc"):
        raise HTTPException(status_code=400, detail="order must be 'asc' or 'desc'")

    sorted_m = sorted(memberships, key=lambda x: x[sort_by], reverse=(order == "desc"))
    return {"sort_by": sort_by, "order": order, "memberships": sorted_m}

@app.post("/memberships", status_code=201)
def enroll_member(request: EnrollRequest):
    global membership_counter

    plan = find_plan(request.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    final_fee, discount_info = calculate_membership_fee(
        plan["price"],
        plan["duration_months"],
        request.payment_mode,
        request.referral_code,
    )

    new_membership = {
        "membership_id": membership_counter,
        "member_name": request.member_name,
        "plan_name": plan["name"],
        "duration": plan["duration_months"],
        "total_fee": final_fee,
        "discount_applied": discount_info,
        "status": "active",
    }

    memberships.append(new_membership)
    membership_counter += 1
    return new_membership

@app.post("/memberships/{membership_id}/freeze")
def freeze_membership(membership_id: int):
    membership = find_membership(membership_id)
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")
    if membership["status"] == "frozen":
        raise HTTPException(status_code=400, detail="Membership is already frozen")

    membership["status"] = "frozen"
    return {"message": "Membership frozen successfully", "membership": membership}

@app.post("/memberships/{membership_id}/reactivate")
def reactivate_membership(membership_id: int):
    membership = find_membership(membership_id)
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")
    if membership["status"] == "active":
        raise HTTPException(status_code=400, detail="Membership is already active")

    membership["status"] = "active"
    return {"message": "Membership reactivated successfully", "membership": membership}

@app.post("/classes/book")
def book_class(request: ClassBookingRequest):
    global class_counter

    member = next(
        (m for m in memberships if m["member_name"] == request.member_name and m["status"] == "active"),
        None,
    )
    if not member:
        raise HTTPException(status_code=403, detail="Active membership required to book classes")

    plan = next((p for p in plans if p["name"] == member["plan_name"]), None)
    if not plan or not plan["includes_classes"]:
        raise HTTPException(status_code=403, detail="Your current plan does not include classes")

    new_booking = {"booking_id": class_counter, **request.dict()}
    class_bookings.append(new_booking)
    class_counter += 1
    return new_booking
