# AI Agent Shell & Environment Instructions

## Shell Environment

**CRITICAL**: This project runs on **Windows PowerShell/CMD**, NOT bash or Unix shells.

### Shell-Specific Command Syntax

Always use Windows command syntax:

| Task | ❌ WRONG (Unix) | ✅ CORRECT (Windows) |
|------|----------------|---------------------|
| Activate venv | `source venv/bin/activate` | `venv\Scripts\activate` |
| Path separator | `/` (forward slash) | `\` (backslash) |
| List directory | `ls` | `dir` or `ls` (PowerShell) |
| Remove file | `rm file.txt` | `del file.txt` or `Remove-Item` |
| Environment variable | `export VAR=value` | `$env:VAR="value"` (PowerShell) or `set VAR=value` (CMD) |
| Copy file | `cp src dest` | `copy src dest` or `Copy-Item` |
| Move file | `mv src dest` | `move src dest` or `Move-Item` |
| Clear screen | `clear` | `cls` or `Clear-Host` |
| File paths | `path/to/file` | `path\to\file` |

### PowerShell vs CMD
- This system uses **CMD (Command Prompt)** by default
- Some PowerShell commands work in CMD, but use CMD-native commands when possible
- **Always use backslashes (`\`) for file paths**

## Django Virtual Environment

### MANDATORY: Always Activate Virtual Environment First

**BEFORE running ANY Python/Django command**, you MUST activate the virtual environment:

```cmd
venv\Scripts\activate
```

### Command Execution Pattern

**ALWAYS follow this pattern**:

```cmd
# Step 1: Activate venv (REQUIRED)
venv\Scripts\activate

# Step 2: Run your Django/Python command
python manage.py runserver
```

### Common Django Commands (with venv activation)

```cmd
# Start development server
venv\Scripts\activate
python manage.py runserver

# Run migrations
venv\Scripts\activate
python manage.py migrate

# Create migrations
venv\Scripts\activate
python manage.py makemigrations

# Create superuser
venv\Scripts\activate
python manage.py createsuperuser

# Collect static files
venv\Scripts\activate
python manage.py collectstatic

# Django shell
venv\Scripts\activate
python manage.py shell

# Run tests
venv\Scripts\activate
python manage.py test

# Check for issues
venv\Scripts\activate
python manage.py check
```

### Installing Python Packages

```cmd
# Always activate venv first!
venv\Scripts\activate
pip install package-name

# Install from requirements.txt
venv\Scripts\activate
pip install -r requirements.txt

# Update requirements.txt
venv\Scripts\activate
pip freeze > requirements.txt
```

## Working Directory

The project root is:
```
c:\Users\DEEPANSHU\Documents\simple-version\copo_management_system
```

All commands should be executed from this directory unless specified otherwise.

## File Path Examples

When referencing files in this project, use Windows path format:

```cmd
# ✅ CORRECT
c:\Users\DEEPANSHU\Documents\simple-version\copo_management_system\manage.py
.\copo_management_system\settings.py
venv\Scripts\activate

# ❌ WRONG
c:/Users/DEEPANSHU/Documents/simple-version/copo_management_system/manage.py
./copo_management_system/settings.py
venv/bin/activate
```

## Python Executable Path

When you need the full Python path (after configuring environment):
```
c:/Users/DEEPANSHU/Documents/simple-version/copo_management_system/venv/Scripts/python.exe
```

Note: Use forward slashes in Python tool calls, but backslashes in terminal commands.

## Environment Detection

If you need to detect the environment:

```cmd
# Check if venv is activated (you should see (venv) in prompt)
echo %VIRTUAL_ENV%

# Check Python path (should point to venv)
where python
```

## Common Mistakes to Avoid

### ❌ DON'T DO THIS:
```bash
# Using Unix commands
source venv/bin/activate
python3 manage.py migrate
ls -la
rm -rf folder

# Running Django commands without activating venv
python manage.py runserver

# Using forward slashes in terminal commands
cd path/to/directory
```

### ✅ DO THIS INSTEAD:
```cmd
# Using Windows commands
venv\Scripts\activate
python manage.py migrate
dir
rmdir /s /q folder

# Always activate venv first
venv\Scripts\activate
python manage.py runserver

# Using backslashes in terminal commands
cd path\to\directory
```

## Multi-Command Sequences

When running multiple commands, activate venv once:

```cmd
# Activate once
venv\Scripts\activate

# Then run multiple commands
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

OR use `&&` to chain commands:

```cmd
venv\Scripts\activate && python manage.py migrate && python manage.py runserver
```

## Node.js / NPM Commands (Tailwind CSS)

NPM commands don't require venv activation:

```cmd
# Install npm packages
npm install

# Run Tailwind in watch mode
npm run dev

# Build Tailwind for production
npm run build
```

## Git Commands

Git commands work the same on Windows (no venv needed):

```cmd
git status
git add .
git commit -m "Your message"
git push origin main
```

## Database Commands

### SQLite (Local Development)
```cmd
# Django ORM shell (requires venv)
venv\Scripts\activate
python manage.py dbshell

# Check database file
dir db.sqlite3
```

### PostgreSQL (Production - Render)
- Managed by Render, no local commands needed
- Access via Render dashboard or connection string

## Terminal Tool Usage

When using the `run_in_terminal` tool:

```python
# ✅ CORRECT - Windows command
run_in_terminal(
    command="venv\\Scripts\\activate && python manage.py migrate",
    explanation="Running database migrations",
    isBackground=False
)

# ❌ WRONG - Unix command
run_in_terminal(
    command="source venv/bin/activate && python manage.py migrate",
    explanation="Running database migrations",
    isBackground=False
)
```

## Quick Reference Card

| Action | Command |
|--------|---------|
| Activate venv | `venv\Scripts\activate` |
| Deactivate venv | `deactivate` |
| Start Django | `venv\Scripts\activate && python manage.py runserver` |
| Run migrations | `venv\Scripts\activate && python manage.py migrate` |
| Install packages | `venv\Scripts\activate && pip install -r requirements.txt` |
| Django shell | `venv\Scripts\activate && python manage.py shell` |
| Create superuser | `venv\Scripts\activate && python manage.py createsuperuser` |
| Check errors | `venv\Scripts\activate && python manage.py check` |
| Run tests | `venv\Scripts\activate && python manage.py test` |
| Collect static | `venv\Scripts\activate && python manage.py collectstatic` |
| Build Tailwind | `npm run build` |
| Watch Tailwind | `npm run dev` |

## Verification Checklist

Before executing any Django command, verify:

- [ ] Am I in the correct directory? (`c:\Users\DEEPANSHU\Documents\simple-version\copo_management_system`)
- [ ] Have I activated the virtual environment? (`venv\Scripts\activate`)
- [ ] Am I using Windows path syntax? (backslashes `\`)
- [ ] Is this a Windows command, not Unix? (no `source`, `ls -la`, etc.)

## Emergency Commands

If something goes wrong:

```cmd
# Kill Django server (if stuck)
Ctrl+C

# Deactivate venv and start fresh
deactivate
venv\Scripts\activate

# Reinstall packages
venv\Scripts\activate
pip install -r requirements.txt

# Reset database (WARNING: deletes all data)
del db.sqlite3
venv\Scripts\activate
python manage.py migrate
```

---

## Summary for AI Agents

**ALWAYS remember:**
1. 🪟 **This is Windows** - use backslashes `\` and Windows commands
2. 🐍 **Activate venv FIRST** - `venv\Scripts\activate` before ANY Django/Python command
3. 📁 **Working directory** - `c:\Users\DEEPANSHU\Documents\simple-version\copo_management_system`
4. ⚡ **PowerShell/CMD** - not bash, not Unix
5. 🔗 **Chain commands** - use `&&` or activate venv once for multiple commands

**When in doubt**: Check if venv is activated, use backslashes, and verify you're using Windows command syntax.
