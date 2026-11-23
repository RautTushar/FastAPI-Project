from math import ceil
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field


app = FastAPI(title="IronFit Gym Management System")


# ---------------------------------------------------------------------------
# In-memory data
# ---------------------------------------------------------------------------

plans = [
    {"id": 1, "name": "Basic", "duration_months": 1, "price": 1000,
     "includes_classes": False, "includes_trainer": False},
    {"id": 2, "name": "Standard", "duration_months": 3, "price": 2500,
     "includes_classes": True, "includes_trainer": False},
    {"id": 3, "name": "Premium", "duration_months": 6, "price": 4500,
     "includes_classes": True, "includes_trainer": True},
    {"id": 4, "name": "Elite", "duration_months": 12, "price": 8000,
     "includes_classes": True, "includes_trainer": True},
    {"id": 5, "name": "Trial", "duration_months": 1, "price": 500,
     "includes_classes": False, "includes_trainer": False},
]

memberships = []
membership_counter = 1

class_bookings = []
class_counter = 1


# ---------------------------------------------------------------------------
# Request models (kept compatible with the original API)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Reusable helper functions
# ---------------------------------------------------------------------------

def find_plan(plan_id: int):
    """Return a plan by ID, or None if it does not exist."""
    return next((plan for plan in plans if plan["id"] == plan_id), None)


def find_membership(membership_id: int):
    """Return a membership by ID, or None if it does not exist."""
    return next(
        (membership for membership in memberships
         if membership["membership_id"] == membership_id),
        None,
    )


def search_items(items, field: str, keyword: str):
    """Case-insensitive partial search for a dictionary field."""
    keyword = keyword.casefold()
    return [
        item for item in items
        if keyword in str(item.get(field, "")).casefold()
    ]


def sort_items(items, sort_by: str, order: str = "asc"):
    """Sort a list of dictionaries by a selected field."""
    return sorted(
        items,
        key=lambda item: item[sort_by],
        reverse=(order == "desc"),
    )


def paginate_items(items, page: int, limit: int):
    """Return pagination metadata and the requested slice."""
    total = len(items)
    total_pages = ceil(total / limit) if total else 0
    start = (page - 1) * limit

    return {
        "total": total,
        "total_pages": total_pages,
        "page": page,
        "limit": limit,
        "items": items[start:start + limit],
    }


def filter_plans_logic(
    data,
    includes_classes=None,
    includes_trainer=None,
    max_price=None,
    duration_months=None,
):
    """Apply all supplied plan filters without changing the source list."""
    results = data

    if includes_classes is not None:
        results = [
            plan for plan in results
            if plan["includes_classes"] == includes_classes
        ]

    if includes_trainer is not None:
        results = [
            plan for plan in results
            if plan["includes_trainer"] == includes_trainer
        ]

    if max_price is not None:
        results = [
            plan for plan in results
            if plan["price"] <= max_price
        ]

    if duration_months is not None:
        results = [
            plan for plan in results
            if plan["duration_months"] == duration_months
        ]

    return results


def calculate_membership_fee(
    base_price: int,
    duration: int,
    payment_mode: str,
    referral: str = "",
):
    """Calculate membership fee using the original discount rules."""
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


# ---------------------------------------------------------------------------
# General
# ---------------------------------------------------------------------------

@app.get("/")
def home():
    return {"message": "Welcome to IronFit Gym"}


# ---------------------------------------------------------------------------
# Plans
# Keep fixed routes before /plans/{plan_id}.
# ---------------------------------------------------------------------------

@app.get("/plans/summary")
def get_plans_summary():
    prices = [plan["price"] for plan in plans]

    return {
        "total_plans": len(plans),
        "with_classes": sum(plan["includes_classes"] for plan in plans),
        "with_trainer": sum(plan["includes_trainer"] for plan in plans),
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
    results = filter_plans_logic(
        plans, includes_classes, includes_trainer, max_price, duration_months
    )
    return {"plans": results, "total": len(results)}


@app.get("/plans/search")
def search_plans(keyword: str = Query(..., min_length=1)):
    results = search_items(plans, "name", keyword)

    if not results:
        return {
            "message": f"No plans found matching '{keyword}'",
            "total_found": 0,
            "results": [],
        }

    return {"total_found": len(results), "results": results}


VALID_PLAN_SORT_FIELDS = ["price", "name", "duration_months"]


@app.get("/plans/sort")
def sort_plans(sort_by: str = "price", order: str = "asc"):
    if sort_by not in VALID_PLAN_SORT_FIELDS:
        raise HTTPException(
            status_code=400,
            detail=f"sort_by must be one of {VALID_PLAN_SORT_FIELDS}",
        )

    if order not in ("asc", "desc"):
        raise HTTPException(
            status_code=400,
            detail="order must be 'asc' or 'desc'",
        )

    return {
        "sort_by": sort_by,
        "order": order,
        "plans": sort_items(plans, sort_by, order),
    }


@app.get("/plans/page")
def paginate_plans(
    page: int = Query(1, ge=1),
    limit: int = Query(2, ge=1),
):
    pagination = paginate_items(plans, page, limit)

    # Preserve the original response field name: "plans".
    return {
        "total": pagination["total"],
        "total_pages": pagination["total_pages"],
        "page": pagination["page"],
        "limit": pagination["limit"],
        "plans": pagination["items"],
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
    results = filter_plans_logic(
        plans, includes_classes, includes_trainer, max_price
    )

    if keyword:
        results = search_items(results, "name", keyword)

    # Retain the original browse endpoint's sorting behavior and response.
    results = sorted(
        results,
        key=lambda item: item.get(sort_by, 0),
        reverse=(order == "desc"),
    )

    pagination = paginate_items(results, page, limit)

    return {
        "metadata": {
            "keyword": keyword,
            "sort_by": sort_by,
            "order": order,
            "total": pagination["total"],
            "pages": pagination["total_pages"],
            "current_page": page,
        },
        "results": pagination["items"],
    }


@app.get("/plans")
def get_all_plans():
    prices = [plan["price"] for plan in plans]

    return {
        "plans": plans,
        "total": len(plans),
        "price_range": {
            "min": min(prices) if prices else 0,
            "max": max(prices) if prices else 0,
        },
    }


@app.get("/plans/{plan_id}")
def get_plan(plan_id: int):
    plan = find_plan(plan_id)

    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")

    return plan


@app.post("/plans", status_code=201)
def add_plan(plan_in: NewPlan):
    if any(
        plan["name"].casefold() == plan_in.name.casefold()
        for plan in plans
    ):
        raise HTTPException(status_code=400, detail="Plan name already exists")

    new_id = max((plan["id"] for plan in plans), default=0) + 1
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

    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")

    if price is not None:
        plan["price"] = price

    if includes_trainer is not None:
        plan["includes_trainer"] = includes_trainer

    return plan


@app.delete("/plans/{plan_id}")
def delete_plan(plan_id: int):
    plan = find_plan(plan_id)

    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")

    active_on_plan = any(
        membership["plan_name"] == plan["name"]
        and membership["status"] == "active"
        for membership in memberships
    )

    if active_on_plan:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete plan with active members",
        )

    plans.remove(plan)
    return {"message": f"Plan '{plan['name']}' deleted successfully"}


# ---------------------------------------------------------------------------
# Memberships
# ---------------------------------------------------------------------------

@app.get("/memberships")
def get_all_memberships():
    return {"memberships": memberships, "total": len(memberships)}


@app.get("/memberships/active")
def get_active_memberships():
    active = [
        membership for membership in memberships
        if membership["status"] == "active"
    ]
    return {"memberships": active, "total": len(active)}


@app.get("/memberships/search")
def search_memberships(member_name: str = Query(..., min_length=1)):
    results = search_items(memberships, "member_name", member_name)

    if not results:
        return {
            "message": f"No memberships found for '{member_name}'",
            "total_found": 0,
            "results": [],
        }

    return {"total_found": len(results), "results": results}


VALID_MEMBERSHIP_SORT_FIELDS = ["total_fee", "duration"]


@app.get("/memberships/sort")
def sort_memberships(sort_by: str = "total_fee", order: str = "asc"):
    if sort_by not in VALID_MEMBERSHIP_SORT_FIELDS:
        raise HTTPException(
            status_code=400,
            detail=f"sort_by must be one of {VALID_MEMBERSHIP_SORT_FIELDS}",
        )

    if order not in ("asc", "desc"):
        raise HTTPException(
            status_code=400,
            detail="order must be 'asc' or 'desc'",
        )

    return {
        "sort_by": sort_by,
        "order": order,
        "memberships": sort_items(memberships, sort_by, order),
    }


@app.post("/memberships", status_code=201)
def enroll_member(request: EnrollRequest):
    global membership_counter

    plan = find_plan(request.plan_id)

    if plan is None:
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

    if membership is None:
        raise HTTPException(status_code=404, detail="Membership not found")

    if membership["status"] == "frozen":
        raise HTTPException(status_code=400, detail="Membership is already frozen")

    membership["status"] = "frozen"
    return {"message": "Membership frozen successfully", "membership": membership}


@app.post("/memberships/{membership_id}/reactivate")
def reactivate_membership(membership_id: int):
    membership = find_membership(membership_id)

    if membership is None:
        raise HTTPException(status_code=404, detail="Membership not found")

    if membership["status"] == "active":
        raise HTTPException(status_code=400, detail="Membership is already active")

    membership["status"] = "active"
    return {"message": "Membership reactivated successfully", "membership": membership}


# ---------------------------------------------------------------------------
# Class bookings
# ---------------------------------------------------------------------------

@app.post("/classes/book")
def book_class(request: ClassBookingRequest):
    global class_counter

    member = next(
        (
            membership for membership in memberships
            if membership["member_name"] == request.member_name
            and membership["status"] == "active"
        ),
        None,
    )

    if member is None:
        raise HTTPException(
            status_code=403,
            detail="Active membership required to book classes",
        )

    plan = next(
        (plan for plan in plans if plan["name"] == member["plan_name"]),
        None,
    )

    if plan is None or not plan["includes_classes"]:
        raise HTTPException(
            status_code=403,
            detail="Your current plan does not include classes",
        )

    new_booking = {"booking_id": class_counter, **request.dict()}
    class_bookings.append(new_booking)
    class_counter += 1

    return new_booking
