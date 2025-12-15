# How the System Works (Simple Explanation)

## The Problem

Multiple lenders (banks/financial companies) work with the same customers.
A customer can apply to 2-3 banks simultaneously and sign contracts with each.
This creates a conflict - several lenders are competing for the same customer.

## The Solution

This system is a shared database where all lenders submit their contracts.
The system automatically detects conflicts and alerts all parties involved.

---

## How It Works

### 1. Lender Registration

An administrator adds a new lender to the system:
- Enter company name
- System generates a secret key (like a password for access)

**Example:** "ABC Bank" receives key `lsp_xxxxx`

---

### 2. Lender Submits Contract

When a customer signs an agreement, the lender sends data to the system:
- Property address
- Customer phone
- Customer email
- Parcel number (if available)
- Signing date

**What happens:**

#### If NO conflicts:
```
Response: "NO_HIT" - you're first, no conflicts
```

#### If conflict EXISTS:
```
Response: "EXISTING_CONTRACT"
Details:
  - Conflict with: "XYZ Bank"
  - They signed: "5 days ago"
  - Matched on: address, phone, email
```

**Additionally:**
- Your contract is saved in the database
- The other lender (XYZ Bank) receives a notification: "Warning! A competitor is working with your customer!"

---

### 3. How the System Finds Conflicts

The system compares the new contract with all active contracts from other lenders in the last 90 days.

**Matches are found by:**
1. **Parcel Number (APN)** (most accurate)
2. **Address + ZIP code**
3. **Customer Email**
4. **Customer Phone**

**Important:** Addresses and phones are normalized to a standard format
- "123 Main Street, Apt 4" = "123 MAIN ST APT 4"
- "(555) 123-4567" = "5551234567"

This eliminates false positives due to different formatting.

---

### 4. Contract Completion

When a lender funds the loan or cancels the deal, they update the status:

#### Option A: Contract Funded
```
Action: Mark as "FUNDED"
Result:
  - Your contract is closed as successful
  - All competitors receive notification:
    "Contract funded by your competitor. You lost."
```

#### Option B: Contract Cancelled
```
Action: Mark as "CANCELLED"
Result:
  - Your contract is closed
  - Competitors receive:
    "Your competitor cancelled their contract. Conflict resolved."
```

---

## Usage Examples

### Scenario 1: No Conflicts

**January 10:**
- ABC Bank submits contract for customer at "123 Main St"
- System: "NO_HIT" (no conflicts)

**January 15:**
- ABC Bank funds the contract
- System: "Contract closed as successful"

### Scenario 2: With Conflict

**January 10:**
- ABC Bank submits contract for "123 Main St", phone 555-1234
- System: "NO_HIT"

**January 12:**
- XYZ Bank submits contract for "123 Main Street", phone (555) 123-4567
- System: "EXISTING_CONTRACT - conflict with ABC Bank"
- ABC Bank receives notification: "Warning! XYZ Bank is also working with your customer"

**January 15:**
- XYZ Bank funds first → marks "FUNDED"
- ABC Bank receives: "Customer funded by XYZ Bank"

**January 16:**
- ABC Bank cancels their contract → "CANCELLED"

---

## Who Sees What?

### Each lender sees:
- ✅ Their own contracts completely
- ✅ Conflict information (other bank name, date)
- ❌ Details of other contracts (amounts, terms, etc.)

### Privacy:
- Other contracts are not visible
- Only see: "conflict with Bank X, signed 5 days ago"
- Customer personal data (phone/email) is not shared with competitors

---

## Notifications (Webhooks)

When an event occurs, the system sends a notification to the lender's server.

**Notification Types:**

1. **NEW_CONFLICT**
   - "A competitor appeared for your contract"
   - Who: bank name
   - When they signed

2. **CONFLICT_RESOLVED**
   - "Competitor cancelled their contract"

3. **CONFLICT_CONTRACT_FUNDED**
   - "Competitor funded the contract. Customer chose them."

---

## System Access

**Web Interface:** http://localhost:8000/docs

Here you can:
- See all available actions
- Submit test contracts
- Check statuses

**Required:**
- Secret key (received during registration)
- Specified in `X-API-Key` header

---

## Actions

### Create Lender
```
POST /admin/lenders
{
  "name": "ABC Bank",
  "webhook_url": "https://your-server.com/webhook"
}

→ Receive api_key (save it!)
```

### Submit Contract
```
POST /lsp/contracts
Header: X-API-Key: your_key
{
  "external_id": "your contract number",
  "address_street": "123 Main St",
  "address_city": "Los Angeles",
  "address_state": "CA",
  "address_zip": "90210",
  "phone": "5551234567",
  "email": "client@email.com",
  "signed_date": "2025-01-15"
}

→ Receive: NO_HIT or EXISTING_CONTRACT with details
```

### Close Contract
```
PUT /lsp/contracts/{id}
Header: X-API-Key: your_key
{
  "status": "FUNDED"  // or "CANCELLED"
}

→ Competitors receive notifications
```

---

## Summary in Simple Terms

**Before:**
- Banks didn't know they were working with the same customer
- Wasted time and money preparing documents
- Discovered conflicts at the last moment

**Now:**
- Bank submits contract → immediately sees if there are competitors
- All parties receive status notifications
- Can quickly decide: continue or step back

**Benefits:**
- Time savings
- Fewer on-ground conflicts
- Process transparency
- Quick decisions

---

## Quick Start

1. **Check the API is running:** http://localhost:8000/health
2. **Open documentation:** http://localhost:8000/docs
3. **Create a test lender:** POST /admin/lenders
4. **Submit a contract:** POST /lsp/contracts (use the api_key from step 3)
5. **Check for conflicts** in the response

---

## Technical Stack (for developers)

- **FastAPI** - Modern Python web framework
- **PostgreSQL** - Database
- **Docker** - Containerization
- **SQLAlchemy** - ORM
- **Pydantic** - Data validation

## Running the System

```bash
# Start
docker-compose up -d

# Check status
curl http://localhost:8000/health

# View logs
docker-compose logs -f api

# Stop
docker-compose down
```
