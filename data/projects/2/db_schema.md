# Database Skeleton: Warehouse Management (WMP)

This database stores structured data related to orders, customers, and inventory for the AI Testing project.

## Tables & Purpose

### 1. orders
Contains all transactional data for customer purchases.
- **Table Entries**:
  - `order_id`: Prime key. Use this for specific order status checks.
  - `customer_id`: Links to the `customers` table.
  - `order_date`: When the order was placed.
  - `total_amount`: Financial value of the order.
  - `status`: Current lifecycle state ('pending', 'processing', 'completed', 'cancelled').

### 2. customers
Stores profile information for registered users.
- **Table Entries**:
  - `customer_id`: Unique identifier.
  - `email`: User's primary contact.
  - `tier`: Customer loyalty level ('gold', 'silver', 'bronze').

### 3. products
Catalog of available items.
- **Table Entries**:
  - `product_id`: Unique SKU.
  - `price`: Unit cost.
  - `stock_level`: Current quantity in warehouse.

---

## Data vs. Document Classification
- **Database Questions**: "How many orders were placed today?", "What is the status of order 5521?", "Show me the top 10 customers by revenue."
- **Document Questions**: "What is the company's return policy?", "How do I handle a damaged shipment?", "Where can I find the employee handbook?"

## Retrieval Strategy
When searching for a specific record (e.g., an order number or customer email), **always** use a direct equality filter (`WHERE order_id = 123`). Do not attempt to load or scan the entire table.
