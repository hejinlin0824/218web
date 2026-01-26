# AGENTS.md - Guidelines for Agentic Coding in this Repository

## Project Overview
This is a Django 6.0.1 web application with three main apps: `core`, `user_app`, and `Github_trend`.

## Build/Lint/Test Commands

### Running Tests
```bash
# Run all tests
python manage.py test

# Run tests for a specific app
python manage.py test user_app
python manage.py test core
python manage.py test Github_trend

# Run a single test (use the full path to the test)
python manage.py test user_app.tests.YourTestCase.test_method_name

# Run with verbosity (more detailed output)
python manage.py test --verbosity=2
```

### Development Commands
```bash
# Run development server
python manage.py runserver

# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Django shell
python manage.py shell
```

## Code Style Guidelines

### Imports
- Order: Standard library → Third-party → Local imports (PEP 8)
- Use `from django.db import models` for model definitions
- Use `from django.shortcuts import render, redirect` for view utilities
- Use `from django.contrib.auth import get_user_model` for User model references
- Keep imports grouped, with blank lines between groups
- Avoid wildcard imports (`from module import *`)

### Naming Conventions
- **Classes**: PascalCase (e.g., `CustomUser`, `EmailBackend`, `GitHubService`)
- **Functions/Methods**: snake_case (e.g., `user_avatar_path`, `register`, `profile`)
- **Variables**: snake_case (e.g., `cache_key`, `repos`, `language`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `API_URL`, `CACHES`)
- **Models**: PascalCase with Meta class using verbose_name for Chinese UI
- **URL pattern names**: lowercase_with_underscores (e.g., `password_reset_confirm`)

### File Upload Pattern
Use UUID-based unique filenames to prevent conflicts:
```python
import uuid, os
def upload_path(instance, filename):
    ext = filename.split('.')[-1]
    return os.path.join('uploads', f'{uuid.uuid4()}.{ext}')
```

### Authentication & Views
- Custom user model: `user_app.CustomUser` (extends AbstractUser)
- Custom backend: `user_app.authentication.EmailBackend` - login with username OR email
- Use `@login_required` decorator for protected views
- Use `messages.success()` for flash messages
- Follow Post/Redirect/Get pattern to prevent duplicate submissions
- Return `render()` with template path and context dictionary

### Forms & URLs
- Forms: Extend Django forms, set `fields` in Meta, add Bootstrap classes in `__init__`
- URLs: Use `app_name` for namespacing, `reverse_lazy()` for success URLs in class-based views
- Include static media serving in DEBUG mode only, use `path()` with named routes

### Models
- Use `verbose_name` for Chinese labels, add `__str__` method
- Use `blank=True, null=True` for optional fields, `default=False` for boolean fields

### Error Handling
- Use try-except for external API calls, log errors: `print(f"Error: {e}")`
- Return sensible defaults (e.g., `[]` for failed API calls)
- Handle `User.DoesNotExist` and `User.MultipleObjectsReturned`, use `response.raise_for_status()`

### Caching
- Use Django cache with LocMemCache in development
- Generate unique cache keys: `f"key_{param1}_{param2}"`
- Set reasonable TTL (e.g., 300 seconds = 5 minutes), check cache before expensive operations

### Environment Variables & Database
- Use `python-dotenv` for `.env` file loading, access with `os.getenv()`
- Never commit `.env` files or secrets
- Use `Q` objects for OR conditions: `Q(username=username) | Q(email=username)`
- Use `get_user_model()` instead of importing User directly
- Be aware of custom user model: `AUTH_USER_MODEL = 'user_app.CustomUser'`
- Use `request.user` for authenticated user, `order_by()` for sorting: `User.objects.filter(...).order_by('id')`

### Comments
- Use Chinese comments with emoji markers (👈 for important notes)
- Keep comments concise, focus on "why" not "what"
- Use docstrings with `"""` following Google/NumPy style

### Templates & Admin
- Templates: root `templates/` directory, app-specific subdirs (e.g., `templates/user_app/`)
- Use Bootstrap classes, pass context dictionaries, `{{ context_var }}` for variables
- Admin: Extend `UserAdmin`, use `add_fieldsets`/`fieldsets`, customize `list_display`, register with `admin.site.register()`

## Configuration
- Settings module: `myweb.settings`
- Database: SQLite3 in development
- Language: `zh-hans` (Simplified Chinese)
- Timezone: UTC
- Debug mode: `True` (disable in production)
- Static files: `static/` directory
- Media files: `media/` directory for uploads

## Special Patterns
- **Email as username**: Custom backend allows login with either username or email
- **UUID file uploads**: Prevents naming collisions for user avatars
- **Caching layer**: Reduces API calls for GitHub trends
- **Custom User Model**: Extends AbstractUser with additional fields (nickname, bio, avatar, email_verified)
- **Service layer pattern**: Extract external API logic into service classes (e.g., `GitHubService`)
- **Class-based views**: Use `as_view()` with class-based auth views, pass `template_name` param
