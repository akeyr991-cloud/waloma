# WALOMA changelog

## Part 2
- Added member directory access for administrators, treasurers, and secretaries, plus administrator account updates and suspension/reactivation.
- Added meeting creation/listing and attendance recording with duplicate prevention.
- Added monthly member contribution obligations, partial payments, outstanding balance calculations, and cash/bank/mobile payment methods.
- Added unique payment receipt numbers and authenticated PDF receipt downloads.
- Added responsive workspace sections for member directory, meetings, contributions, balances, payment history, and receipt downloads.
- Added Alembic migration `0002_operations`.
- Kept all Part 1 authentication, registration, roles, logo, and setup files in the same `WALOMA/` project.

## Part 1
- Added FastAPI project foundation, SQLAlchemy models, Alembic, PostgreSQL configuration, authentication, role checks, registration, and approval workflow.
