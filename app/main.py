from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app import models
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os

load_dotenv()

models.Base.metadata.create_all(bind=engine)

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")


# -----------------------------
# CHANGE CALCULATION
# -----------------------------
def calculate_change(balance, denominations):
    result = {}

    for value in sorted(denominations.keys(), reverse=True):
        count = min(balance // value, denominations[value])
        if count > 0:
            result[value] = int(count)
            balance -= value * count

    return result, balance


# -----------------------------
# EMAIL FUNCTION
# -----------------------------
def send_invoice_email(email, items, total_without_tax, total_tax, net_price, paid, balance):
    try:
        import os
        import smtplib
        from email.mime.text import MIMEText

        EMAIL_USER = os.getenv("EMAIL_USER")
        EMAIL_PASS = os.getenv("EMAIL_PASS")

        # Start message
        message = f"""
Thank you for your purchase!

Customer Email: {email}

Items:
"""

        # Add items
        for item in items:
            message += f"""
Product {item['id']}: Qty {item['qty']} × ₹{item['price']:.2f} = ₹{item['purchase_price']:.2f} (Tax: ₹{item['tax_amount']:.2f})
"""

        # Add totals
        message += f"""

Total without tax: ₹{total_without_tax:.2f}
Total tax: ₹{total_tax:.2f}
Net price: ₹{net_price:.2f}

Paid: ₹{paid:.2f}
"""

        # Payment status
        if paid > net_price:
            message += f"Change: ₹{balance:.2f}\n"
        elif paid < net_price:
            message += f"Pending: ₹{net_price - paid:.2f}\n"
        else:
            message += "Payment: Exact\n"

        # Create email
        msg = MIMEText(message)

        msg["Subject"] = "Your Invoice - Thank You for Shopping"
        msg["From"] = EMAIL_USER
        msg["To"] = email

        # Send email
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, email, msg.as_string())
        server.quit()

        print("✅ Email sent successfully")

    except Exception as e:
        print("❌ Email failed:", e)

# -----------------------------
# BILLING PAGE
# -----------------------------
@app.get("/")
def billing_page(request: Request):
    return templates.TemplateResponse("billing_page.html", {"request": request})


# -----------------------------
# GENERATE BILL
# -----------------------------
@app.post("/generate-bill")   # ✅ KEEP THIS SAME
async def generate_bill(request: Request, background_tasks: BackgroundTasks):

    form = await request.form()

    email = form.get("email")

    # ✅ FIXED FIELD NAMES (IMPORTANT)
    product_ids = form.getlist("product_ids")
    quantities = form.getlist("quantities")

    paid = float(form.get("paid"))

    # ✅ FIXED DENOMINATION NAMES
    denominations = {
        500: int(form.get("d500") or 0),
        200: int(form.get("d200") or 0),
        100: int(form.get("d100") or 0),
        50: int(form.get("d50") or 0),
        20: int(form.get("d20") or 0),
        10: int(form.get("d10") or 0),
        5: int(form.get("d5") or 0),
        2: int(form.get("d2") or 0),
        1: int(form.get("d1") or 0)
    }

    db: Session = SessionLocal()

    items = []
    total_without_tax = 0
    total_tax = 0

    for pid, qty in zip(product_ids, quantities):

        product = db.query(models.Product).filter(
            models.Product.id == int(pid)
        ).first()

        if not product:
            return templates.TemplateResponse(
                "billing_page.html",
                {"request": request, "error": f"Product {pid} not found"}
            )

        qty = int(qty)

        purchase_price = product.price * qty
        tax = purchase_price * (product.tax / 100)
        total = purchase_price + tax

        items.append({
            "id": product.id,
            "price": product.price,
            "qty": qty,
            "purchase_price": purchase_price,
            "tax_percent": product.tax,
            "tax_amount": tax,
            "total": total
        })

        total_without_tax += purchase_price
        total_tax += tax

    net_price = total_without_tax + total_tax
    balance = round(paid - net_price, 2)

    # ✅ CHANGE LOGIC FIX
    if balance > 0:
        change, remaining = calculate_change(int(balance), denominations)
        if remaining > 0:
            change["Remaining"] = remaining
    elif balance < 0:
        change = {"Amount Due": abs(balance)}
    else:
        change = {}

    # SAVE PURCHASE
    purchase = models.Purchase(customer_email=email)
    db.add(purchase)
    db.commit()
    db.refresh(purchase)

    for item in items:
        purchase_item = models.PurchaseItem(
            purchase_id=purchase.id,
            product_id=item["id"],
            quantity=item["qty"]
        )
        db.add(purchase_item)

    db.commit()

    # EMAIL
    background_tasks.add_task(
    send_invoice_email,
    email,
    items,
    total_without_tax,
    total_tax,
    net_price,
    paid,
    balance
)

    return templates.TemplateResponse(
        "invoice.html",
        {
            "request": request,
            "email": email,
            "items": items,
            "total_without_tax": total_without_tax,
            "total_tax": total_tax,
            "net_price": net_price,
            "paid": paid,
            "balance": balance,
            "change": change
        }
    )


# -----------------------------
# HISTORY
# -----------------------------
@app.get("/history")
def purchase_history(request: Request):
    db: Session = SessionLocal()
    purchases = db.query(models.Purchase).all()

    return templates.TemplateResponse(
        "history.html",
        {"request": request, "purchases": purchases}
    )


# -----------------------------
# DETAILS
# -----------------------------
@app.get("/purchase/{purchase_id}")
def purchase_detail(request: Request, purchase_id: int):
    db: Session = SessionLocal()

    purchase = db.query(models.Purchase).filter(
        models.Purchase.id == purchase_id
    ).first()

    return templates.TemplateResponse(
        "purchase_detail.html",
        {"request": request, "purchase": purchase}
    )