# Smart Retail POS — Full-Stack Supermarket & Store Checkout System

<div align="center">

[![Daily Streak](https://img.shields.io/badge/Daily%20Streak-Active%20%F0%9F%94%A5-brightgreen?style=flat-square&logo=github)](https://github.com/abdussatarkhan)
[![Software Portfolio](https://img.shields.io/badge/Portfolio-Software%20Engineering%20%26%20Systems-0e75b6?style=flat-square&logo=github)](https://github.com/abdussatarkhan)
[![Author: Abdussatar](https://img.shields.io/badge/Author-Abdussatar-24292e?style=flat-square&logo=github)](https://github.com/abdussatarkhan)

</div>

[![CI](https://github.com/abdussatarkhan/point-of-sale-/actions/workflows/ci.yml/badge.svg)](https://github.com/abdussatarkhan/point-of-sale-/actions)
[![Flask](https://img.shields.io/badge/Flask-Web_Framework-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![MySQL](https://img.shields.io/badge/MySQL-Relational_DB-4479A1?style=for-the-badge&logo=mysql&logoColor=white)](https://www.mysql.com/)
[![JavaScript](https://img.shields.io/badge/JavaScript-Cashier_Register_UI-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)](https://developer.mozilla.org/)

> **A full-stack retail checkout and store inventory management system powered by Python Flask and MySQL. Supports instant USB barcode scanning, split-tender payments (Cash, Card, Credit), discount engines, receipt generation, and real-time inventory deductions.**

---

## 🏛️ System Architecture

```mermaid
graph TD
    Scanner[Barcode Scanner & POS Cashier Terminal] --> FlaskApp[Flask Backend Routing & API]
    FlaskApp --> TxManager[Transaction & Split-Tender Payment Engine]
    TxManager --> MySQL[(MySQL Database: Products, Orders, Inventory, Users)]
    TxManager --> Inventory[Inventory Decrementing & Low-Stock Alerts]
    TxManager --> Receipt[Receipt Generator & Cash Drawer Pulse]
```

---

## 🌟 Key Features & Capabilities

- **🛒 High-Speed Barcode Checkout**: Automated barcode scanner listener designed for rapid supermarket cashier workflows with instant product resolution and quantity incrementing.
- **💳 Split-Tender Payment Engine**: Supports flexible customer checkout across multiple payment methods in a single order (Cash, Debit/Credit Card, Store Credit).
- **📦 Real-Time Inventory Control**: Automated stock level decrements on completed transactions with low-inventory warnings displayed on cashier screens.
- **🧾 Shift Balancing & Auditing**: End-of-shift cashier balance reports reconciling cash drawer collections against computerized order logs.

---

## 🚀 Quickstart & Setup

### Prerequisites
- [Python 3.10+](https://www.python.org/downloads/)
- [MySQL 8.0+](https://www.mysql.com/downloads/)

### 1. Clone the Repository
```bash
git clone https://github.com/abdussatarkhan/point-of-sale-.git
cd point-of-sale-
```

### 2. Environment Setup & Database Configuration
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure database credentials in config.py or create a .env file:
# DB_HOST=localhost
# DB_USER=root
# DB_PASSWORD=your_password
# DB_NAME=pos_db

# Run database migration (if needed)
# mysql -u root -p pos_db < migrate_v2.sql

# Start the POS server
python app.py
```

Access the POS cashier portal at:
`http://localhost:5000`

---

## 🖥️ Application & Operational Interface

<p align="center">
  <img src="screenshots/01_dashboard_preview.png" alt="Smart Retail POS Cashier & Inventory Console Preview" width="95%" />
</p>

> [!TIP]
> You can also explore [`dashboard.html`](dashboard.html) directly in any modern browser for a standalone interface walkthrough.

---

## 🗺️ Roadmap & Upcoming Enhancements

- [x] Flask + MySQL cashier and split-tender payment engine
- [x] Barcode scanner integration and inventory tracking
- [x] Receipt generation and shift closing summaries
- [ ] USB ESC/POS thermal receipt printer raw socket driver
- [ ] Offline browser cart caching with IndexedDB
- [ ] Multi-store stock transfer and replenishment requests

---

## 👨‍💻 Author & Contact

Built and maintained by **Abdussatar** ([@abdussatarkhan](https://github.com/abdussatarkhan)).  
For technical discussions, collaboration, or queries, feel free to reach out via [LinkedIn](https://www.linkedin.com/in/abdus-satar-5150813b5/) or [GitHub](https://github.com/abdussatarkhan).

---

## 📜 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

### 👨‍💻 Maintained by [Abdussatar (@abdussatarkhan)](https://github.com/abdussatarkhan)
Part of the **[Abdussatar Software Engineering & Systems Portfolio](https://github.com/abdussatarkhan)**.

⭐ If you find this project valuable, consider dropping a star! ⭐

</div>
