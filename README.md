<p align="center">
  <img src=app/static/img/logo/logo.jpg width="350">
</p>

<h1 align="center">FastAPI HTMX</h1>

<p align="center">
  Web App providing boilerplate implementation for user management, roles, groups, and CRUD operations using  HTMX, FastAPI and AlpineJS for rapid prototyping and without worrying for the user management.
</p>

## External Libraries Used

This project leverages several external libraries to provide a robust and efficient solution. Below is a brief description of each library along with a link to their documentation:

- [FastAPI](https://fastapi.tiangolo.com/) (0.143.0): A modern, fast (high-performance), web framework for building APIs and serving HTML templates with Python 3.6+ based on standard Python type hints.
- [SQLAlchemy](https://www.sqlalchemy.org/) (2.0.54): The Python SQL toolkit and Object Relational Mapper that gives application developers the full power and flexibility of SQL.
- [FastAPI Users](https://fastapi-users.github.io/fastapi-users/) (15.0.5): Ready-to-use and customizable users management for FastAPI.
- [Uvicorn](https://www.uvicorn.org/) (0.54.0): A lightning-fast ASGI server implementation, using `uvloop` and `httptools`.
- [Jinja2](https://palletsprojects.com/p/jinja/) (3.1.6): A modern and designer-friendly templating language for Python.
- [NH3](https://github.com/Th3Whit3Wolf/nh3) (0.3.7): A Python binding to the HTML sanitizer `h3`.
- [Alembic](https://alembic.sqlalchemy.org/en/latest/) (1.20.0): A lightweight database migration tool for usage with the SQLAlchemy Database Toolkit.
- [AlpineJS](https://alpinejs.dev/) (3.17.4, vendored in `app/static/vendor/`, see `VENDORED.md`): A rugged, minimal framework for composing JavaScript behavior in your HTML templates.
- [Flowbite](https://flowbite.com/) (JS 4.0.2, vendored in `app/static/vendor/`, see `VENDORED.md`): A component library built on top of Tailwind CSS for building modern web interfaces.
- [Pydantic](https://docs.pydantic.dev/2.0/) (2.14.1): Data validation and settings management using Python type annotations.

## Features Implemented

- User Authentication and Authorization
- Role Management
- Group Management
- Dashboard for managing users, roles, and groups
- RESTful API endpoints for CRUD operations
- HTML templates for the web interface
- Database migrations with Alembic
- Unified error handling approach.

## To-Do (Future Enhancements)

- 🎨 Implement Theming using Flowbite and Tailwind
- 🚦 Implement a rate limiter to prevent abuse and ensure fair usage
- ✅ 📦 Integrate MinIO object storage for efficient file saving and management **[Completed]**
- 🔑 Add functionality to allow users to update their passwords
- 🔄 Implement a password reset feature on the login page
- ⚡ Implement rendering of blocks using FastAPI Fragment instead of reloading complete page or partials **[In Progress]**
- 📝 Develop a logging service to track and analyze user activity
- ✅ 🛡️ Implement CSRF protection to enhance security **[Completed]**
- 💾 Integrate Neon database (SQLite) for production use **[In Progress]**
- ✅ 🎨 Replace HyperScript code with Alpine JS **[Completed]**
- ✅ 🚀 Boilerplate code to work with Python 12 and HTMX 2 **[Completed]**
- ✅ 📱 Fixing the GUI issues appearing in mobile view **[Completed]**
- 🧪 Add more tests
- 🔧 Wrapper to handle the pydantic models inputs efficiently from front end **[In Progress]**

## Demo

<p align="center">
  <img src=app/static/img/logo/FastAPI-HTMX.gif>
</p>

## Admin Login Credential

- **email:** superuser@admin.com
- **password:** password123

## Quick Setup Using PowerShell Script

For Windows users, you can use the provided `setup.ps1` script to automate the setup and management of your FastAPI-HTMX project. This script covers all essential project operations. Note: `setup.ps1` still expects poetry and is not updated for uv yet.

### Available Commands

| Command     | Description                         |
| ----------- | ----------------------------------- |
| setup       | Complete project setup              |
| install     | Install dependencies only           |
| env         | Create .env file                    |
| migrate     | Run database migrations             |
| init-db     | Initialize database with migrations |
| run         | Start the application               |
| run-dev     | Start in development mode           |
| credentials | Show admin login credentials        |
| status      | Show project status                 |
| clean       | Clean up generated files            |

### Usage

1. **Open PowerShell** and navigate to your project directory:
   ```powershell
   cd "C:\Users\mahmad\Desktop\Coding\FastAPI-HTMX"
   ```
2. **Run a command** (for example, to set up the project):
   ```powershell
   .\setup.ps1 setup
   ```
   Or to start the application:
   ```powershell
   .\setup.ps1 run
   ```

---

## Setup With uv

You need Python 3.12 and [uv](https://docs.astral.sh/uv/).

1. **Clone the repository:**

   ```sh
   git clone https://github.com/maanas/FastAPI-HTMX.git
   cd FastAPI-HTMX
   ```

2. **Install dependencies.** This creates `.venv` from `uv.lock` (runtime and dev tools):

   ```sh
   uv sync
   ```

3. **Create the `.env` file** and edit it. At least replace the `change-me-...` secrets:

   ```sh
   cp .env.example .env
   ```

4. **Create the database** from the committed migration:

   ```sh
   .venv/bin/alembic upgrade head
   ```

   If you have a database that was created before the migration existed, run
   `.venv/bin/alembic stamp 0001_initial_schema` once instead. To add the next migration, see
   `app/migrations/README`.

5. **Start the application:**

   ```sh
   .venv/bin/python main.py
   ```

   It serves on `http://127.0.0.1:8080` (API docs at `/docs`).

6. **Run the tests.** Run them after step 4: they use the database `DATABASE_URL` points to.

   ```sh
   .venv/bin/python -m pytest -q app/tests
   ```

### Environment Variables

`.env.example` lists every variable with a placeholder value that works for local development
over http. Copy it to `.env` and edit it. The app does not start without the variables marked
required.

| Variable | Required | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | yes | Database URL, SQLite by default (`sqlite+aiosqlite:///./users.db`) |
| `AUTH_SECRET` | no, but set it | Signs the login token. Falls back to a built-in default if missing |
| `MINIO_URL` | yes | MinIO server URL |
| `MINIO_ACCESS_KEY` | yes | MinIO access key |
| `MINIO_SECRET_KEY` | yes | MinIO secret key |
| `MINIO_BUCKET` | yes | MinIO bucket name |
| `MINIO_SECURE` | no (`false`) | `true` for HTTPS to MinIO. Use it in production |
| `CSRF_SECRET_KEY` | yes | Signs the CSRF token |
| `COOKIE_SAMESITE` | yes | CSRF cookie SameSite: lowercase `lax`, `strict` or `none`. `none` needs `COOKIE_SECURE=true` |
| `COOKIE_SECURE` | yes | `false` for local http, `true` in production (HTTPS) |

**Note:** While using placeholder MinIO credentials will allow the database to record file uploads, the actual files won't be stored without valid MinIO server credentials. For full file storage functionality, set up a MinIO server or use valid MinIO service credentials.

## Updating Model References in `init_models`

When you define a new **Database model** in your application, it's essential to update the `init_models` function to ensure that Alembic can detect and generate migrations for this new model correctly. This step is crucial for maintaining the integrity of your database schema and ensuring that all models are correctly versioned.

### Steps to Update `init_models`

1. **Locate `init_models` Function**: Open the `base.py` file in `app/database/base.py`. This file contains the `init_models` function, which is responsible for importing all the models in your application.

2. **Add New Model Import**: Once you have defined a new model in your application, you need to import it in the `init_models` function. Ensure that you follow the existing import structure. For example, if your new model is `Invoice` and it's located in the `models.financial` module, you would add the following line:

   ```python
   from ..models.financial import Invoice  # noqa: F401
   ```

   The `# noqa: F401` comment at the end of the import statement tells the linter to ignore the "imported but unused" warning, as the import is necessary for Alembic to detect and generate migrations for the model.

3. **Follow Import Conventions**: If you have multiple models in the same module, you can import them in a single line to keep the `init_models` function organized. For example:

   ```python
   from ..models.financial import Invoice, Payment, Transaction  # noqa: F401
   ```

4. **Save Changes**: After adding the import statement for your new model, save the changes to the `base.py` file.

5. **Generate Alembic Migration**: With the new model imported in the `init_models` function, you can now generate an Alembic migration script that includes this model. Run the Alembic command to autogenerate a migration (see `app/migrations/README`):

   ```bash
   .venv/bin/alembic revision --autogenerate --rev-id 0002_invoice -m "Added new model Invoice"
   ```

6. **Review and Apply Migration**: Always review the generated migration script to ensure it accurately represents the changes to your models. After reviewing, apply the migration to update your database schema:

   ```bash
   .venv/bin/alembic upgrade head
   ```

## Project Structure

Below is an overview of the project structure for application. This structure is designed to organize the application's components logically, making it easier to navigate and maintain.

```bash
FastAPI-HTMX/
├── app/
│ ├── core/             # Core application logic and utilities
│ │ ├── config.py         # Application configuration
│ │ └── security.py       # Security utilities
│ ├── database/         # Database configurations and connections
│ │ ├── base.py           # Base database setup
│ │ └── session.py        # Database session management
│ ├── migrations/         # Alembic migration scripts
│ ├── models/           # SQLAlchemy ORM models
│ │ ├── groups.py         # Group model definitions
│ │ ├── roles.py          # Role model definitions
│ │ └── users.py          # User model definitions
│ ├── routes/           # API route definitions
│ │ ├── api/
│ │ │ ├── auth.py         # Authentication endpoints
│ │ │ └── users.py        # User management endpoints
│ │ └── view/           # View routes for web interface
│ │   ├── group.py        # Group management views
│ │   ├── role.py         # Role management views
│ │   └── view_crud.py    # SQLAlchemyCRUD class
│ ├── schema/           # Pydantic schemas
│ │ ├── group.py          # Group schemas
│ │ ├── role.py           # Role schemas
│ │ └── user.py           # User schemas
│ ├── static/           # Static files
│ │ ├── css/              # Stylesheets
│ │ ├── js/               # JavaScript files
│ │ └── img/              # Images and assets
│ └── templates/        # Jinja2 HTML templates
│   ├── auth/             # Authentication templates
│   ├── components/       # Reusable components
│   └── partials/         # Partial templates
├── tests/              # Unit and integration tests
├── .env                # Environment variables (copy of .env.example, not committed)
├── .env.example        # Template for .env
├── alembic.ini         # Alembic configuration
├── main.py             # Application entry point
├── pyproject.toml      # Project configuration and pinned dependencies
├── uv.lock             # Locked dependencies (uv)
└── README.md           # Project documentation
```

## ER Diagram

Here's the Entity-Relationship (ER) diagram for database:

![ER Diagram](app/static/img/logo/er_diagram.png)

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any changes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
