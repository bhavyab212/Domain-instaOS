# InstaOS Store Policies & Standard Operating Procedures (SOP)
**Brand**: InstaOS Streetwear Direct-to-Consumer (D2C)  
**Control Center**: Nonilion.com Virtual Office Room  
**System Architecture**: Autonomous Multi-Agent Operations Engine  

---

## 1. Executive Summary & Brand Overview
InstaOS operates an autonomous Instagram direct-to-consumer streetwear brand managed directly through a virtual command office on Nonilion.com. Customer interactions, order capture, payment verification, courier dispatching, and post-order tracking are executed end-to-end without manual human intervention unless high-risk fraud guards or out-of-stock edge cases are triggered.

---

## 2. Pricing, Discounts & Taxation Rules

### 2.1 Goods & Services Tax (GST) Policy
- **Included Tax Structure**: All catalog retail prices shown to customers are **inclusive of 12% GST** (Apparel & Streetwear category).
- **Tax Breakdown Formula**:
  $$\text{Taxable Value} = \text{Subtotal} - \text{GST Amount}$$
  $$\text{GST Amount (12\%)} = \text{Round}\left(\frac{\text{Discounted Subtotal} \times 12}{112}, 2\right)$$
  - **CGST (6%)**: $50\%$ of GST Amount
  - **SGST (6%)**: $50\%$ of GST Amount
- **GSTIN**: `07AAAAA0000A1Z5` (InstaOS Apparel Technologies Pvt Ltd).

### 2.2 Volume & Promotional Discounts
- **Bulk Purchase Incentive**: Any order with **3 or more total units** ($\ge 3$ items across any SKUs or single SKU) automatically receives an autonomous **10% Bulk Discount** applied to the item subtotal prior to shipping or COD surcharges.
- **Formula**:
  $$\text{Discount} = \begin{cases} \text{Round}(\text{Subtotal} \times 0.10, 2) & \text{if } \text{Total Quantity} \ge 3 \\ 0.00 & \text{otherwise} \end{cases}$$

### 2.3 Payment Methods & Surcharges
1. **Prepaid UPI / Instant Bank Transfer**:
   - Zero convenience fee (₹0 surcharge).
   - Instant order confirmation and immediate dispatch to fulfillment.
2. **Cash on Delivery (COD)**:
   - Fixed **₹50 Cash Handling Surcharge** added to final invoice.
   - Subject to High-Value COD Fraud Verification Guard.

---

## 3. Risk Management & High-Value COD Fraud Hold SOP

### 3.1 High-Value COD Risk Threshold
- Any order placed with payment mode `COD` having a final invoice value **greater than ₹2,500** is automatically flagged:
  - **Status**: `ON_HOLD (High Value COD > ₹2500)`
  - **Fulfilment Stage**: `AWAITING_MANAGER_APPROVAL`
  - **Risk Grade**: `HIGH_RISK_COD`
- **Action**: No warehouse packing slip or AWB is issued. The system alerts the Nonilion Virtual Office Room and prompts the store manager for human override (`@InstaOS approve <ORD_ID>`) or cancellation (`@InstaOS cancel <ORD_ID>`).

### 3.2 Customer Identity Verification (`verifly` engine)
Before confirmation, buyer details are checked for synthetic identity patterns:
- **Mobile Number Validation**: Must be a valid 10-digit Indian telecom number matching `^[6-9]\d{9}$`.
- **Pincode Validation**: Must be a valid 6-digit Indian postal code matching `^\d{6}$`.
- **Disposable Handle / Syntax Checks**: Identifies temporary handles or suspicious patterns.
- **Scorecard**: Buyer assigned either `VERIFIED_BUYER` (Emerald badge) or `UNVERIFIED_SYNTAX` (Rose badge).

---

## 4. Edge-Case Guards & Backorder Handling

### 4.1 Mandatory Qualification Rule #5 (Incomplete Address Guard)
- **Hard Gate**: An order intent MUST supply:
  1. Complete street address / locality
  2. 6-digit Indian Postal Pincode
  3. 10-digit Customer Mobile Number
- **Enforcement**: If either the pincode or phone number is missing, the system **MUST NOT** confirm the order, deduct inventory, or generate an invoice.
- **Autonomous Response**: The agent replies in courteous Hinglish/English pointing out the missing field and asking the customer to provide their pincode or 10-digit number.

### 4.2 Out-of-Stock Backorder Queuing
- When a requested SKU/size has `0` available stock (e.g. Acid Wash Hoodie Size XL):
  - The agent does not abruptly cancel or decline the customer.
  - The customer is automatically registered in the in-memory **Backorder Waitlist**.
  - A Nonilion Virtual Office action is dispatched (`walk_to_user` targeting `@StoreManager`) alerting the floor manager to order fabric and restock.
  - When inventory is replenished via `@InstaOS restock`, the waitlist is automatically resolved and customer notifications are staged.

### 4.3 Low-Stock Threshold
- Any SKU size with $\le 2$ units remaining is flagged as `LOW_STOCK` in the warehouse audit report to trigger supplier purchase orders.

---

## 5. Logistics, Courier Zone Allocation & Autonomous Delivery Pipeline

### 5.1 Courier Routing by Indian Pincode Zones
To optimize delivery SLAs and shipping charges, orders are dynamically routed to 3 primary courier partners:
1. **Delhivery Express Air (`DL...`)**:
   - Pincodes starting with Northern zones: `11`–`19` (Delhi NCR, Haryana, Punjab, Himachal, J&K), `20`–`28` (Uttar Pradesh, Uttarakhand), `30`–`34` (Rajasthan).
2. **BlueDart Priority Air (`BD...`)**:
   - Pincodes starting with Western and Southern zones: `40`–`49` (Maharashtra, Goa, MP, Gujarat), `50`–`69` (Telangana, Andhra Pradesh, Karnataka, Tamil Nadu, Kerala).
3. **XpressBees D2C Surface (`XB...`)**:
   - Pincodes starting with Eastern and North-Eastern zones: `70`–`79` (West Bengal, Odisha, North East), `80`–`89` (Bihar, Jharkhand).

### 5.2 Autonomous Lifecycle State Transitions
Confirmed orders are scheduled on an asynchronous background coroutine advancing fulfillment every 15 seconds:
1. `CONFIRMED` $\to$ `PACKED` (Pick & pack completed in warehouse, invoice generated)
2. `PACKED` $\to$ `IN_TRANSIT` (Handed over to courier hub, AWB active)
3. `IN_TRANSIT` $\to$ `OUT_FOR_DELIVERY` (Arrived at destination delivery hub)
4. `OUT_FOR_DELIVERY` $\to$ `DELIVERED` (Final customer drop completed)

Every state change triggers:
- Multi-agent audit trail logging
- Automated CSV master report re-generation
- Real-time room broadcast to Nonilion.com.
