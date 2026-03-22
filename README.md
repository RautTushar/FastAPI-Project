# IronFit Gym Management System

A REST API built with **FastAPI** for managing gym memberships, plans, and class bookings.  
This is a final project for a FastAPI internship training — covers all concepts from Day 1 to Day 6.

---

## Tech Stack

- **Python 3.8+**
- **FastAPI** — web framework
- **Uvicorn** — ASGI server
- **Pydantic** — request validation

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/your-username/ironfit-gym.git
cd ironfit-gym
```

### 2. Install dependencies

```bash
pip install fastapi uvicorn
```

### 3. Run the server

```bash
python -m uvicorn main:app --reload
```

### 4. Open Swagger UI

```
http://127.0.0.1:8000/docs
```

> All endpoints can be tested directly in Swagger UI — no extra tools needed.

---

## API Endpoints

### Plans

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/plans` | Get all plans with price range |
| GET | `/plans/summary` | Total plans, class/trainer counts, min/max price |
| GET | `/plans/filter` | Filter by classes, trainer, max price, duration |
| GET | `/plans/search` | Search plans by keyword |
| GET | `/plans/sort` | Sort by price, name, or duration |
| GET | `/plans/page` | Paginate plans |
| GET | `/plans/browse` | Filter + sort + paginate combined |
| GET | `/plans/{plan_id}` | Get a single plan by ID |
| POST | `/plans` | Add a new plan (201) |
| PUT | `/plans/{plan_id}` | Update price or trainer inclusion |
| DELETE | `/plans/{plan_id}` | Delete a plan (blocked if active members exist) |

### Memberships

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/memberships` | Get all memberships |
| GET | `/memberships/active` | Get only active memberships |
| GET | `/memberships/search` | Search by member name |
| GET | `/memberships/sort` | Sort by total fee or duration |
| POST | `/memberships` | Enroll a new member (201) |
| POST | `/memberships/{id}/freeze` | Freeze a membership |
| POST | `/memberships/{id}/reactivate` | Reactivate a frozen membership |

### Classes

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/classes/book` | Book a class (requires active membership with class access) |

---

## Membership Plans

| Plan | Duration | Price | Classes | Trainer |
|------|----------|-------|---------|---------|
| Trial | 1 month | ₹500 | No | No |
| Basic | 1 month | ₹1,000 | No | No |
| Standard | 3 months | ₹2,500 | Yes | No |
| Premium | 6 months | ₹4,500 | Yes | Yes |
| Elite | 12 months | ₹8,000 | Yes | Yes |

---

## Fee Calculation Logic

- **6-month plan** → 10% discount
- **12-month plan** → 20% discount
- **EMI payment** → ₹200 processing charge added
- **Referral code** → extra 5% off on top of any discount

---

## Example Requests

**Enroll a member**
```json
POST /memberships
{
  "member_name": "Rahul Sharma",
  "plan_id": 4,
  "phone": "9876543210",
  "start_month": "Jan",
  "payment_mode": "cash",
  "referral_code": "FRIEND10"
}
```

**Filter plans**
```
GET /plans/filter?includes_classes=true&max_price=5000
```

**Browse plans (combined)**
```
GET /plans/browse?keyword=e&includes_classes=true&sort_by=price&order=asc&page=1&limit=2
```

---

## Project Structure

```
ironfit/
└── main.py       # all routes, models, and helper functions
```

---

## Concepts Covered

| Day | Concept |
|-----|---------|
| Day 1 | GET endpoints, JSON responses, home route |
| Day 2 | POST with Pydantic validation (Field, min_length, gt) |
| Day 3 | Helper functions, filter logic with `is not None` checks |
| Day 4 | Full CRUD — POST, PUT, DELETE with 201/404 status codes |
| Day 5 | Multi-step workflow — enroll → freeze → reactivate → book class |
| Day 6 | Search, sort, pagination, and combined browse endpoint |

---

## Notes

- Data is stored in memory — it resets when the server restarts
- All fixed routes (`/plans/summary`, `/plans/search`, etc.) are placed **above** variable routes (`/plans/{plan_id}`) to avoid routing conflicts
- Business rule: a plan cannot be deleted if any active member is enrolled on it

---

## Author

Built as a FastAPI internship final project.
