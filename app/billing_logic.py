def calculate_bill(products, quantities):
    
    total_without_tax = 0
    total_tax = 0
    items = []

    for product, qty in zip(products, quantities):

        price = product.price * qty
        tax = price * (product.tax / 100)

        items.append({
            "name": product.name,
            "qty": qty,
            "price": price,
            "tax": tax
        })

        total_without_tax += price
        total_tax += tax

    total = total_without_tax + total_tax

    return {
        "items": items,
        "total_without_tax": total_without_tax,
        "tax": total_tax,
        "total": total
    }


def calculate_change(balance, denominations):
    
    result = {}

    for d in sorted(denominations, reverse=True):

        count = balance // d
        balance %= d

        if count:
            result[d] = count

    return result