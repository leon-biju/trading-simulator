# Copilot Instructions

This document provides guidance for AI coding agents to effectively contribute to the `trading-simulator` project.

## Project Overview & Architecture

This is a monolithic Django application that simulates a trading platform. The project is organized into a modular structure with distinct responsibilities for each component. The primary development environment is managed by Docker.

The main components are located in the `apps/` directory:

-   `apps/accounts`: Handles user registration, authentication, and profile management. It uses a `CustomUser` model.
-   `apps/wallets`: Manages user wallets and transactions. A key pattern here is the use of a **service layer** (`services.py`) to encapsulate business logic for wallet operations (e.g., `create_wallet`, `deposit`).
-   `apps/market`: Defines the financial instruments available for trading (e.g., stocks, crypto).
-   `apps/trading`: Contains the core logic for executing trades.
-   `apps/dashboard`: Provides users with a view of their account and wallet information.

Communication between apps is often handled via **Django Signals**. For example, a signal in `apps/accounts/signals.py` is likely responsible for creating a new wallet via the wallet service whenever a new user is created.

## Developer Workflow

### Local Development

The entire local development environment is orchestrated with Docker.

-   To start the application (web server and database), run:
    ```bash
    docker-compose up --build
    ```
-   The application will be accessible at `http://127.0.0.1:8000`.

### Database Migrations

The project uses Django's built-in migration system. To create or apply migrations, you need to run commands inside the `web` container.

-   To create new migrations after a model change:
    ```bash
    docker-compose exec web python manage.py makemigrations
    ```
-   To apply migrations:
    ```bash
    docker-compose exec web python manage.py migrate
    ```

### Testing

The project uses `pytest` for testing. Tests are located in each app's `tests/` directory, further divided into `unit/` and `integration/` folders.

-   To run all tests, execute `pytest` inside the `web` container:
    ```bash
    docker-compose exec web pytest
    ```
-   To run tests for a specific app or file:
    ```bash
    docker-compose exec web pytest apps/wallets/tests/
    ```

## Code Conventions

-   **Service Layer**: Encapsulate complex business logic within `services.py` files inside an app. This keeps views and models cleaner. For an example, see `apps/wallets/services.py`.
-   **Environment Variables**: All configuration, especially secrets and environment-specific settings, should be managed with environment variables. In local development, these are loaded from a `.env` file at the project root. Refer to `config/settings.py` to see how they are used.
-   **Modular Apps**: Continue the pattern of separating concerns into distinct Django apps within the `apps/` directory.
-   **Templates**: Global templates are in the root `templates/` directory. App-specific templates are located in `apps/<app_name>/templates/`.
