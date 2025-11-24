# 📝 Task Management System (Python Django)

A robust and scalable **Task Manager API** built using **Python Django & Django REST Framework**, supporting task creation, updates, filtering, searching, sorting, pagination, tagging, soft delete, and user assignment.

---

## 🚀 Features

- Create, read, update, and delete tasks (CRUD)
- Soft delete with `is_deleted` and `deleted_at`
- Task filtering (status, priority, due date, tags)
- Search by title and description
- Sorting by priority, due date, created date
- Pagination support
- User assignment (`created_by` & `assigned_to`)
- Tagging system (Many-to-Many)
- Authentication using Django's built-in user model
- Fully documented APIs (Postman Collection included)

---

## 🛠️ Tech Stack

- **Python 3.12**
- **Django 4.x**
- **Django REST Framework**
- **SQLite**
- **Postman** for API testing
**link** : https://inventory-1173.postman.co/workspace/inventory-Workspace~b0df5fb5-1253-465e-82f6-be6967628eeb/request/35166923-8464f265-1d29-4563-b2f2-d64d9aa3289d?action=share&creator=35166923
---


---

## ⚙️ Installation & Setup

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/muhammedkm10/taskXBackend.git
python -m venv env
env\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver



