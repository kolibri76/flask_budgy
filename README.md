# Budgy
flask_budgy is a simple budget app to record your receipts and expenditures.  This application was developed as part of the CS50 final project.

Details:
- Responsive design (in order to use on mobile devices)
- Admin Interface (manage users & default categories)
- Option to store attachments (e.g. receipts for expenditures) to transactions
- Option to store geo location to transactions

Setup commands:
  1. flask db upgrade
  2. python manage.py init_db
  3. adjust config parameters in application.py
  4. flask run
  
Login to app:
  user: admin@budgy.tld
  pw: password
