from odoo_client import OdooClient


def main():
    print("Connecting to Odoo...")

    odoo = OdooClient()

    print("Connected successfully.")

    customer_id = odoo.create_customer(
        name="Prototype Customer",
        email="prototype.customer@example.com",
        phone="+351 900 000 000"
    )

    print(f"Created customer in Odoo. Customer ID: {customer_id}")

    customers = odoo.get_customers(limit=10)

    print("\nLatest customers from Odoo:")

    for customer in customers:
        print(
            f"ID: {customer['id']} | "
            f"Name: {customer.get('name')} | "
            f"Email: {customer.get('email')} | "
            f"Phone: {customer.get('phone')}"
        )


if __name__ == "__main__":
    main()