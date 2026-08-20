def calculate_charge_and_profit(amount):
    """
    Calculate the transaction charge and profit.
    Logic:
        ₦1,000 – ₦9,999 → ₦100
        ₦10,000 – ₦19,999 → ₦200
    Profit = Charge (for now)
    """
    if 1000 <= amount <= 9999:
        charge = 100
    elif 10000 <= amount <= 19999:
        charge = 200
    else:
        charge = 0  # Adjust if needed for other ranges

    profit = charge  # Currently profit is the same as charge
    return charge, profit
