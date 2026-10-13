
CREATE DATABASE IF NOT EXISTS cloudcart;
USE cloudcart;

-- 1. Users
CREATE TABLE IF NOT EXISTS users (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'customer'
) ENGINE=InnoDB;

-- 2. Products
CREATE TABLE IF NOT EXISTS products (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    stock_quantity INT NOT NULL DEFAULT 0,
    image_key VARCHAR(255),
    CHECK (price >= 0),
    CHECK (stock_quantity >= 0)
) ENGINE=InnoDB;

-- 3. Orders
CREATE TABLE IF NOT EXISTS orders (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL,
    total_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (total_amount >= 0),
    FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB;

-- 4. Order Items
CREATE TABLE IF NOT EXISTS order_items (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    order_id BIGINT UNSIGNED NOT NULL,
    product_id BIGINT UNSIGNED NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    CHECK (quantity > 0),
    CHECK (unit_price >= 0),
    FOREIGN KEY (order_id)
        REFERENCES orders(id)
        ON DELETE CASCADE,
    FOREIGN KEY (product_id)
        REFERENCES products(id)
) ENGINE=InnoDB;

-- 5. Payments
CREATE TABLE IF NOT EXISTS payments (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    order_id BIGINT UNSIGNED NOT NULL UNIQUE,
    payment_method VARCHAR(30) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    CHECK (amount >= 0),
    FOREIGN KEY (order_id) REFERENCES orders(id)
) ENGINE=InnoDB;
