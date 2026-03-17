from pydantic import BaseModel

class ProductCreate(BaseModel):
    name: str
    stock: int
    price: float
    tax: float


class PurchaseItem(BaseModel):
    product_id: int
    quantity: int


class BillRequest(BaseModel):
    email: str
    items: list[PurchaseItem]
    paid_amount: float