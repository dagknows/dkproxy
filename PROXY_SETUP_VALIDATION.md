# Proxy Setup Validation - Enhanced Error Handling

## Problem

After running `install_proxy.sh`, the `.env` file should contain required environment variables like:
- `PROXY_ALIAS`
- `DAGKNOWS_URL`
- `DAGKNOWS_PROXY_URL`
- `PROXY_SESSION_ID`
- `SUPER_USER_ORG` (optional)

However, the `.env` file was missing these variables, causing errors when starting the proxy:

```
WARN[0000] The "PROXY_ALIAS" variable is not set. Defaulting to a blank string.
WARN[0000] The "DAGKNOWS_URL" variable is not set. Defaulting to a blank string.
...
project name must not be empty
make: *** [Makefile:18: down] Error 1
```

## Root Cause

The `install_proxy.sh` script runs three commands:
1. `dk proxy list` - Lists existing proxies
2. `dk proxy new <name>` - Creates new proxy on server
3. `dk proxy getenv <name>` - Fetches environment variables from server and writes to `.env`

If any of these fail (especially `dk proxy getenv`), the `.env` file will be missing or incomplete.

Common causes:
1. **Authentication failure** - `dk config init` didn't complete successfully
2. **Proxy creation failure** - User doesn't have permissions to create proxies
3. **Server communication issue** - Can't reach DagKnows server
4. **API endpoint failure** - `/getProxyEnv` endpoint returned empty or error

## Solution

Enhanced the installation wizard with comprehensive validation at each step:

### 1. Enhanced `dk config init` Validation

**Before:**
```python
# Just ran the command and hoped it worked
subprocess.run(f"{dk_path} config init --api-host {server_url}", shell=True, check=True)
print_success("DagKnows CLI configured successfully")
```

**After:**
```python
# Run the command
subprocess.run(f"{dk_path} config init --api-host {server_url}", shell=True, check=True)

# Verify it actually works by trying to list proxies
result = run_command(f"{dk_path} proxy list 2>&1", capture_output=True, check=False)
if result and "error" in result.lower() and "401" in result:
    print_error("Authentication failed. Please check your credentials.")
    return False

print_success("DagKnows CLI configured and verified successfully")
```

### 2. Enhanced Proxy Setup Validation

**Before:**
```python
# Run install_proxy.sh
subprocess.run(cmd, shell=True, check=True)
print_success(f"Proxy '{proxy_name}' created successfully")
```

**After:**
```python
# Run install_proxy.sh
subprocess.run(cmd, shell=True, check=True)
print_success("install_proxy.sh completed")

# Verify .env file was created
if not os.path.exists('.env'):
    print_error(".env file was not created!")
    print_error("This usually means:")
    print_error("  1. dk proxy new failed - proxy wasn't created on server")
    print_error("  2. dk proxy getenv failed - couldn't retrieve env vars")
    print_error("  3. Authentication issue - check your dk config")
    return False

# Check for ALL required environment variables
required_vars = {
    'PROXY_ALIAS': 'The name/alias of the proxy',
    'DAGKNOWS_URL': 'The main DagKnows server URL',
    'DAGKNOWS_PROXY_URL': 'The DagKnows proxy/wsfe URL',
    'PROXY_SESSION_ID': 'The proxy session identifier'
}

# Parse .env and check for missing variables
missing_vars = {}
for var, description in required_vars.items():
    if var not in env_content or not env_content[var]:
        missing_vars[var] = description

if missing_vars:
    print_error(f"❌ {len(missing_vars)} required variable(s) missing!")
    # Show which variables are missing and their descriptions
    # Show current .env contents
    # Provide fix instructions
    return False
else:
    print_success("✓ All required environment variables found!")
    # Display the values for user verification
```

### 3. Enhanced Start Proxy Validation

**Before:**
```python
# Just tried to start without checking
if use_sg:
    cmd = "sg docker -c 'make up logs'"
else:
    cmd = "make up logs"
subprocess.run(cmd, shell=True, check=True)
```

**After:**
```python
# Verify .env exists
if not os.path.exists('.env'):
    print_error(".env file not found!")
    print_info("Please run: dk proxy getenv <proxy_name>")
    return False

# Check for required variables
required_vars = ['DAGKNOWS_URL', 'PROXY_ALIAS', 'DAGKNOWS_PROXY_URL']
missing = [var for var in required_vars if var not in env_vars or not env_vars[var]]

if missing:
    print_error(f"❌ Missing required variables: {', '.join(missing)}")
    # Show current .env contents
    # Provide fix instructions
    return False

# Now try to start
subprocess.run(cmd, shell=True, check=True)
```

### 4. Graceful Failure Handling

If proxy doesn't start:
- Installation doesn't fail completely
- Shows "Installation Incomplete" message
- Provides step-by-step troubleshooting instructions
- Still displays all post-installation steps

## User Experience

### When Everything Works ✓

```
============================================================
           Setting Up DagKnows Proxy
============================================================

...

✓ install_proxy.sh completed

ℹ Verifying proxy configuration...
✓ All required environment variables found!

  PROXY_ALIAS: myproxy
  DAGKNOWS_URL: https://192.168.1.100
  DAGKNOWS_PROXY_URL: https://192.168.1.100/wsfe
  PROXY_SESSION_ID: abc123...
```

### When .env is Missing ❌

```
✗ .env file was not created!
✗ This usually means:
  1. dk proxy new failed - proxy wasn't created on server
  2. dk proxy getenv failed - couldn't retrieve env vars from server
  3. Authentication issue - check your dk config

ℹ To debug:
  1. source ~/dkenv/bin/activate
  2. dk proxy list  (check if proxy exists)
  3. dk proxy getenv myproxy  (try to get env vars)
```

### When .env Has Missing Variables ❌

```
✗ ❌ 3 required environment variable(s) are missing or empty!

  Missing: PROXY_ALIAS
           The name/alias of the proxy
  Missing: DAGKNOWS_URL
           The main DagKnows server URL
  Missing: DAGKNOWS_PROXY_URL
           The DagKnows proxy/wsfe URL

⚠ Current .env file contents:
  PROXY_NAME=myproxy
  (other vars if any)

✗ The proxy will NOT start without these variables!

ℹ To fix this:
  1. Make sure the proxy was created successfully:
     source ~/dkenv/bin/activate && dk proxy list
  2. Regenerate the .env file:
     dk proxy getenv myproxy
  3. Verify .env has content:
     cat .env
```

## How dk proxy getenv Works

1. Connects to DagKnows server using credentials from `dk config init`
2. Calls API endpoint: `/getProxyEnv` with payload: `{"alias": "proxy_name"}`
3. Server returns JSON with `envfile` object containing all environment variables
4. Writes these variables to `.env` file

If any step fails, `.env` will be empty or missing.

## Required Environment Variables

Based on the documentation and docker-compose.yaml:

| Variable | Description | Example |
|----------|-------------|---------|
| `PROXY_ALIAS` | Proxy name/identifier | `myproxy` |
| `DAGKNOWS_URL` | Main DagKnows server URL | `https://192.168.1.100` |
| `DAGKNOWS_PROXY_URL` | DagKnows wsfe endpoint | `https://192.168.1.100/wsfe` |
| `DAGKNOWS_EXECSWS_URL` | Execution websocket URL | `https://192.168.1.100/...` |
| `PROXY_SESSION_ID` | Unique session identifier | Generated by server |
| `SUPER_USER_ORG` | Organization identifier | Optional |
| `VERBOSE` | Enable verbose logging | `true` or `false` |

## Debugging Steps for Users

If `.env` is missing or incomplete:

### Step 1: Check dk config
```bash
source ~/dkenv/bin/activate
dk config init --api-host https://your-server
```

### Step 2: Verify authentication
```bash
dk proxy list
```
Should show list of proxies (may be empty). If you get an authentication error, rerun `dk config init`.

### Step 3: Check if proxy was created
```bash
dk proxy list
```
Look for your proxy name in the list.

### Step 4: Regenerate .env file
```bash
dk proxy getenv myproxy
```
This should create/update the `.env` file.

### Step 5: Verify .env has content
```bash
cat .env
```
Should show all the environment variables.

### Step 6: Start proxy
```bash
make up logs
```

## Files Modified

- `install.py` - Enhanced validation in:
  - `configure_dk_cli()` - Verify authentication works
  - `setup_proxy()` - Validate .env file and required variables
  - `start_proxy()` - Check variables before starting
  - `print_final_instructions()` - Handle partial success

## Testing

To test the validation:

1. **Test missing .env**:
   ```bash
   rm .env
   python3 install.py
   # Should detect missing .env and show helpful error
   ```

2. **Test incomplete .env**:
   ```bash
   echo "PROXY_NAME=test" > .env
   python3 install.py
   # Should detect missing required variables
   ```

3. **Test authentication failure**:
   ```bash
   # Provide wrong credentials during dk config init
   # Should detect and report authentication failure
   ```

## Benefits

1. **Early failure detection** - Catches issues before attempting to start proxy
2. **Clear error messages** - Users know exactly what went wrong
3. **Actionable guidance** - Step-by-step instructions to fix issues
4. **Better debugging** - Shows current state (.env contents, missing vars)
5. **Prevents silent failures** - No more "worked but didn't work" scenarios

