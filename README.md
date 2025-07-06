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

## Decisions

The system was designed with simplicity in mind, focusing on essential features for loan management and fraud detection.
The API endpoints are structured to allow both users and administrators to interact with the system effectively, categorized under two
major collections, `Users` and `Loans`.

Our Fraud Detection Unit is integrated into the loan approval process, allowing administrators to flag suspicious applications for further review, as
well as approve or reject loans based on the application's risk profile. There is also an automated fraud detection mechanism that flags applications based on predefined criteria.

> :Important: Do note, this system does not allow auto-approval of loans. All applications must be reviewed by an administrator. Fraud patterns are detected and flagged for manual review,
> upon which decisions rests with the `LoanAdmin`.

## Features

- User registration and login
- Granualar user roles (`Customer`, `LoanAdmin`)
- Consistent API design
- Simplified loan application process

## Fraud Detection Mechanism

Fundamentally, when a user applies for a loan, the system checks for certain criteria that may indicate potential fraud. If any of these criteria are met, the application is flagged for review by a `LoanAdmin`.
Upon review, the `LoanAdmin` can either approve or reject the loan application based on the risk profile and other factors.

## Getting Started

### Prerequisites

```
- Python 3.13
- Django
```

### Installation

The project is entirely managed using `uv`, a virtual environment manager for Python. To set up the project, follow these steps:

1. Install `uv` if you haven't already:
   ```bash
   pip install uv
   ```
2. Clone the repository:

   ```bash
    git clone --depth 1 https://github.com/50-Course/loan-management-system.git
   ```

3. Navigate to the project directory:

   ```bash
    cd loan-management-system
   ```

4. Create a virtual environment and run uv sync:

   ```bash
   uv venv && uv sync
   ```

5. Apply migrations to set up the database - we use SQLite for simplicity:
   ```bash
    uv run python manage.py migrate
   ```
   or from within the virtual environment:
   ```bash
   python manage.py migrate
   ```
6. Runserver to start the application:
   ```bash
   uv run python manage.py runserver
   ```
   or from within the virtual environment:
   ```bash
   python manage.py runserver
   ```

There is also a `Dockerfile` included for quick bootstrapping the application in a containerized environment.
To use Docker, ensure you have Docker installed and run the following commands:

    ```bash
    docker build -t loan-management-system .
    docker run -p <your-preffered-port>:<the-container-port> loan-management-system
    ```

### Testing

The project includes a combination of integration (e2e) and functional tests (unit tests) to ensure the critical parts of the system works as expected.
While TDD was not strictly followed, I am more of a BDD (Behavior-Driven Development, a subset of TDD inclined towards behavior) enthusiast, and I have included tests that cover the main functionalities of the system.
And for this simple project, that is sufficient. The project runs an automated CI pipeline to ensure reliability of the system at any time, however, you may run tests locally with the following commands:

```bash
uv run pytest .
```

...from the project root.

or from within an active virtual environment:

```bash
python manage.py test
```

### Contributing

Contributions are welcome! If you have suggestions for improvements or new features, feel free to open an issue or submit a pull request.
In fact, we encourage you to contribute to the project by adding new features, fixing bugs, or improving documentation. Migrating from 'static'
system to self-learning, pattern-recognizing system is a great way to start. I plan on exploring the intersection of AI and Fraud Detection in future iterations of this project or elsewhere.

### License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### Author

This project was created by [50-Course](mailto:eridotdev@gmail.com)
