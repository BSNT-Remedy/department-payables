# 📊 Department Payables Management System

A desktop application for managing student payables and payments, built with **Flask**, **SQLite**, and **PyWebview**.  
Designed for the Departments to track student bills efficiently.

---

## 🚀 Features
- Student registration with unique student number format (`##-##-##`)
- Manage student payables with checkbox selection
- Auto-calculated total payable amount
- Search bar for student number and name
- Payment page showing total, rendered amount, change, and balance
- Simple and lightweight SQLite database

---

## 🛠️ Tech Stack
- **Backend**: Flask + SQLAlchemy (SQLite)
- **Frontend**: HTML, CSS (via Flask templates) + PyWebview
- **Database**: SQLite
- **Platform**: Desktop (via PyWebview wrapper)

---

## 📂 Project Structure
department-payables/
│-- app.py # Main Flask application
│-- /templates # HTML templates
│-- /static # CSS, JS, assets
│-- /models # Database models
│-- requirements.txt
│-- .gitignore
│-- README.md


---

## ⚙️ Installation & Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/BSNT-Remedy/department-payables.git
   cd department-payables
   ```
2. Create a virtual environment:
  ```bash
  python -m venv venv
  source venv/bin/activate   # On Linux/Mac
  venv\Scripts\activate      # On Windows
  ```
3. Install dependencies:
```bash
pip install -r requirements.txt
```
4. Run the app:
```bash
python app.py
```

✨ Future Improvements
- Add authentication (admin & student login)
- Export reports as PDF/Excel
- Improve UI design
- Add notifications system

👨‍💻 Author
Developed by Allan Jay Busante
