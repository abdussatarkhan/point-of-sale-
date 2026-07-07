-- Counter POS — v2 migration
-- Run this ONCE against your existing database to add the columns/tables
-- the v2 Register (discounts + split payments) needs.
--
-- Usage:
--   mysql -u root -p counter_pos < migrate_v2.sql
--
-- Safe to run even if some/all of this was already applied — every
-- statement below checks first and skips itself if there's nothing to do.

USE counter_pos;

-- 1. Add discount_type to sales, if it isn't already there
SET @col_exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'sales' AND COLUMN_NAME = 'discount_type'
);
SET @sql := IF(@col_exists = 0,
  'ALTER TABLE sales ADD COLUMN discount_type ENUM(''fixed'',''percent'') NOT NULL DEFAULT ''fixed'' AFTER discount',
  'SELECT ''discount_type already exists, skipping'' AS status'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 2. Widen payment_method on sales (in case it's still a narrow/old ENUM)
ALTER TABLE sales MODIFY payment_method VARCHAR(40) NOT NULL DEFAULT 'cash';

-- 3. Create sale_payments (split-tender support), if it doesn't exist yet
CREATE TABLE IF NOT EXISTS sale_payments (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    sale_id     INT NOT NULL,
    method      ENUM('cash','card','mobile_wallet','credit','other') NOT NULL DEFAULT 'cash',
    amount      DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE
) ENGINE=InnoDB;

SELECT 'Migration complete.' AS status;
