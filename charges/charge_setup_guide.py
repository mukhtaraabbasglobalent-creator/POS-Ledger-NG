def charge_setup_guide():

    print("""
====================================
      CHARGE SETUP GUIDE
====================================

POS Ledger NG does NOT import charges automatically.

Reason:

• POS charges are different in every state.
• Charges vary by provider.
• Each business decides its own charges.
• Providers can change their fees at any time.

Recommendation:

1. Add your Provider
2. Create your Charge Profile
3. Enter your own:
   - Minimum Amount
   - Maximum Amount
   - Customer Charge
   - Provider Fee

The calculator will automatically use
your own charges.

====================================
""")

    input("Press Enter to continue...")
