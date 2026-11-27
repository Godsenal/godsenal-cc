def receipt_line(order_id, amount, charge_id):
    return f"order {order_id}: {amount:,} (charge {charge_id})"
