def calculate_order_total(items, delivery_price, discount):
    items_total = 0

    for item in items:
        items_total += item["price"] * item["quantity"]
    total_price = items_total - discount
    if total_price < 0:
        total_price = 0
    total_price += delivery_price
    return {
        "items_total": items_total,
        "discount": discount,
        "delivery_price": delivery_price,
        "total_price": total_price
    }



