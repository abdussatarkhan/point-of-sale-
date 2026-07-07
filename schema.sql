-- Counter POS — MySQL Schema
-- Run: mysql -u root -p < schema.sql

CREATE DATABASE IF NOT EXISTS counter_pos CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE counter_pos;

-- ------------------------------------------------------------
-- Users (cashiers / admins)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name     VARCHAR(100) NOT NULL,
    role          ENUM('admin', 'cashier') NOT NULL DEFAULT 'cashier',
    is_active     TINYINT(1) NOT NULL DEFAULT 1,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Categories
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS categories (
    id    INT AUTO_INCREMENT PRIMARY KEY,
    name  VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Products / Inventory
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS products (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    sku           VARCHAR(50) NOT NULL UNIQUE,
    barcode       VARCHAR(50) UNIQUE,
    name          VARCHAR(150) NOT NULL,
    category_id   INT,
    price         DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    cost_price    DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    stock_qty     INT NOT NULL DEFAULT 0,
    low_stock_at  INT NOT NULL DEFAULT 5,
    is_active     TINYINT(1) NOT NULL DEFAULT 1,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE INDEX idx_products_name ON products(name);

-- ------------------------------------------------------------
-- Sales (one row per completed transaction)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sales (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    invoice_no    VARCHAR(30) NOT NULL UNIQUE,
    user_id       INT NOT NULL,
    subtotal      DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    discount      DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    discount_type ENUM('fixed','percent') NOT NULL DEFAULT 'fixed',
    tax           DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    total         DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    amount_paid   DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    change_due    DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    payment_method VARCHAR(40) NOT NULL DEFAULT 'cash',
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB;

CREATE INDEX idx_sales_created ON sales(created_at);

-- ------------------------------------------------------------
-- Sale line items
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sale_items (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    sale_id     INT NOT NULL,
    product_id  INT NOT NULL,
    product_name VARCHAR(150) NOT NULL,   -- snapshot, survives product edits
    unit_price  DECIMAL(10,2) NOT NULL,
    qty         INT NOT NULL,
    line_total  DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id)
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Sale payments — supports split tender (e.g. part cash + part card)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sale_payments (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    sale_id     INT NOT NULL,
    method      ENUM('cash','card','mobile_wallet','credit','other') NOT NULL DEFAULT 'cash',
    amount      DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- Seed data
-- ------------------------------------------------------------
-- Default admin login: username=admin / password=admin123
-- (hash generated with werkzeug.security.generate_password_hash)
INSERT INTO users (username, password_hash, full_name, role) VALUES
('admin', 'scrypt:32768:8:1$kMrEWj3CYSXdZL3D$a5d42d32b06e959b2f2f33481f57a8963bcd8686e5f846c8ad93a190a967480b83b86abfa98df06cdf61c4d18eee1139a8137bc0011995375f0c1602da19ad0f', 'Store Admin', 'admin')
ON DUPLICATE KEY UPDATE username=username;

INSERT INTO categories (name) VALUES ('General'), ('Beverages'), ('Snacks'), ('Household')
ON DUPLICATE KEY UPDATE name=name;

-- ------------------------------------------------------------
-- Migrating an existing database from the previous version?
-- Run these instead of the whole file:
--
--   ALTER TABLE sales ADD COLUMN discount_type ENUM('fixed','percent') NOT NULL DEFAULT 'fixed' AFTER discount;
--   ALTER TABLE sales MODIFY payment_method VARCHAR(40) NOT NULL DEFAULT 'cash';
--   CREATE TABLE IF NOT EXISTS sale_payments (
--       id INT AUTO_INCREMENT PRIMARY KEY,
--       sale_id INT NOT NULL,
--       method ENUM('cash','card','mobile_wallet','credit','other') NOT NULL DEFAULT 'cash',
--       amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
--       FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE
--   ) ENGINE=InnoDB;
-- ------------------------------------------------------------
