# Virtual Environment Activation Fix

## Problem

The `dk` CLI commands were being called directly using the full path (`~/dkenv/bin/dk`), which could cause issues with Python dependencies not being properly loaded. When you use the full path to a Python script in a virtual environment without activating it first, the script runs but the Python environment (PYTHONPATH, installed packages, etc.) may not be set up correctly.

### Example of the Issue

**Incorrect (what we were doing):**
```bash
~/dkenv/bin/dk proxy list
```

This runs the `dk` command, but Python might not find the dependencies installed in the venv (like `requests`, `typer`, etc.).

**Correct (what we should do):**
```bash
source ~/dkenv/bin/activate && dk proxy list
```

This activates the virtual environment first, setting up all the necessary environment variables, then runs the `dk` command.

## Root Cause

When you activate a virtual environment with `source ~/dkenv/bin/activate`, it does several things:
1. Sets `VIRTUAL_ENV` environment variable
2. Modifies `PATH` to prioritize venv binaries
3. Updates `PYTHONPATH` to include venv's site-packages
4. Sets `PYTHONHOME` if needed
5. Updates shell prompt to show venv is active

Running `~/dkenv/bin/dk` directly bypasses all of this setup, which can lead to:
- Import errors (can't find installed packages)
- Version conflicts (might use system Python packages instead of venv packages)
- Configuration issues (wrong config paths)

## Solution

Updated all `dk` command invocations to activate the virtual environment first.

### Changes Made

#### 1. Check DagKnows CLI Version

**Before:**
```python
result = run_command(f"{dk_path} version 2>&1", capture_output=True, check=False)
```

**After:**
```python
result = run_command("source ~/dkenv/bin/activate && dk version 2>&1", 
                    capture_output=True, check=False)
```

#### 2. Verify CLI Configuration

**Before:**
```python
result = run_command(f"{dk_path} proxy list 2>&1", capture_output=True, check=False)
```

**After:**
```python
result = run_command("source ~/dkenv/bin/activate && dk proxy list 2>&1", 
                    capture_output=True, check=False)
```

#### 3. Configure DagKnows CLI

**Before:**
```python
subprocess.run(f"{dk_path} config init --api-host {server_url}", 
              shell=True, check=True)
```

**After:**
```python
subprocess.run(f"source ~/dkenv/bin/activate && dk config init --api-host {server_url}", 
              shell=True, check=True, executable='/bin/bash')
```

Note: We also added `executable='/bin/bash'` to ensure the shell used supports `source` command.

#### 4. Verify Configuration After Init

**Before:**
```python
result = run_command(f"{dk_path} proxy list 2>&1", capture_output=True, check=False)
```

**After:**
```python
result = run_command("source ~/dkenv/bin/activate && dk proxy list 2>&1", 
                    capture_output=True, check=False)
```

## Already Correct

The `setup_proxy()` function was already correctly using venv activation:

```python
cmd = f"source ~/dkenv/bin/activate && sh install_proxy.sh {proxy_name}"
subprocess.run(cmd, shell=True, check=True, executable='/bin/bash')
```

This was working correctly because `install_proxy.sh` needs to run `dk proxy new` and `dk proxy getenv`, which require the venv to be active.

## Why This Matters

### Scenario 1: Import Errors
Without activating the venv, `dk` might fail with:
```
ModuleNotFoundError: No module named 'requests'
ModuleNotFoundError: No module named 'typer'
```

### Scenario 2: Version Conflicts
If the system has older versions of dependencies, `dk` might:
- Use wrong package versions
- Have unexpected behavior
- Fail silently or with cryptic errors

### Scenario 3: Authentication Issues
The `dk` CLI stores configuration in `~/.dk/config`. Without proper venv activation:
- Config might not be read correctly
- Authentication tokens might not work
- API calls might fail

## Testing

To verify the fix works:

### Test 1: Version Command
```bash
# This should work now
python3 install.py
# During venv verification, it should show the correct dk version
```

### Test 2: Configuration
```bash
# During dk config init step, it should successfully authenticate
python3 install.py
# Enter server URL and credentials
# Should verify configuration with "dk proxy list"
```

### Test 3: Proxy Creation
```bash
# The entire proxy setup should work
python3 install.py
# Should create proxy and generate .env file successfully
```

## Code Pattern

**Always use this pattern for dk commands:**

```python
# Single command
cmd = "source ~/dkenv/bin/activate && dk <command>"
subprocess.run(cmd, shell=True, executable='/bin/bash')

# With output capture
cmd = "source ~/dkenv/bin/activate && dk <command> 2>&1"
result = run_command(cmd, capture_output=True, check=False)

# Multiple commands
cmd = "source ~/dkenv/bin/activate && dk command1 && dk command2"
subprocess.run(cmd, shell=True, check=True, executable='/bin/bash')
```

**Never do this:**

```python
# DON'T use direct path without activation
dk_path = os.path.expanduser('~/dkenv/bin/dk')
subprocess.run(f"{dk_path} command", shell=True)
```

## Files Modified

- `install.py`:
  - `setup_virtual_environment()` - Fixed version check
  - `configure_dk_cli()` - Fixed config init and verification
  - Removed unused `dk_path` variables in `configure_dk_cli()`

## Related Documentation

- Python venv docs: https://docs.python.org/3/library/venv.html
- What `source activate` does: https://docs.python.org/3/library/venv.html#how-venvs-work

## Benefits

1. **Reliability** - Commands work consistently regardless of system Python setup
2. **Isolation** - Uses correct dependencies from venv, not system packages
3. **Consistency** - Matches how users manually run dk commands
4. **Debugging** - Easier to troubleshoot (same as manual usage)
5. **Best Practice** - Follows Python virtual environment conventions

## Prevention

To prevent this issue in the future:

1. **Always activate venv** before running Python scripts from it
2. **Test in clean environment** where system packages differ from venv
3. **Document the requirement** that dk must be run with venv active
4. **Use explicit activation** rather than relying on PATH tricks

## User Impact

This fix ensures that:
- ✅ `dk version` shows correct version
- ✅ `dk config init` works properly
- ✅ `dk proxy list` authenticates correctly
- ✅ `dk proxy new` creates proxies successfully
- ✅ `dk proxy getenv` generates proper .env files
- ✅ All dk commands have access to required dependencies

Without this fix, any of the above could fail with cryptic errors or silent failures.

