# Loan Management System

With built-in Fraud Detection Mechanism

## System Architecture

### Design

Actors: User - divided into two; Customer, LoanAdmin

## API Design:

```
User APIs:

    POST /register/: Register new user

    POST /login/: Token-based login

Loan APIs:

    POST /loan/: Submit a loan application (user)

    GET /loans/requests/: View all loan applications (user)

    GET /loans/{id}/: View specific loan application (user)

    Admin-only:
        GET /loans/: View all loan applications (admin)

        GET /loans/{id}/: View specific loan application (admin)

        POST /loans/{id}/approve/: Approve a loan

        POST /loans/{id}/reject/: Reject a loan

        POST /loans/{id}/flag/: Mark as flagged

        GET /loans/flagged/: View all flagged loans
```
