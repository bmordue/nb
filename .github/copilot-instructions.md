# NewsBlur Story Processing Application (nb)

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Application Overview
nb is a Python 3 background service that processes news stories from NewsBlur feeds. It runs scheduled tasks to fetch story hashes, populate story details, add comment counts, manage domains, and prune starred stories. The application supports multiple database backends (SQLite, PostgreSQL, MySQL, DynamoDB) and uses monitoring via Datadog and Rollbar.

## Working Effectively

### Bootstrap Environment and Dependencies
- **CRITICAL**: Set appropriate timeouts (60+ minutes) for all build commands. NEVER CANCEL builds or long-running commands.
- Create Python virtual environment: `python3 -m venv .env` -- takes 1-3 minutes
- Activate environment: `source .env/bin/activate`
- Upgrade pip: `pip install --upgrade pip` -- may fail due to network timeouts, can be skipped
- Install dependencies: `pip install -r src/requirements.txt` -- takes 30 seconds to 5 minutes depending on network. NEVER CANCEL. Set timeout to 15+ minutes.
- **Network Issues**: pip commands may fail with "Read timed out" or "Temporary failure in name resolution". Retry commands if network connectivity issues occur.

### Application Configuration and Database Setup
- Initialize configuration: `python src/set_defaults.py` -- creates default config in SQLite database
- Creates `nb.sqlite` database with default configuration including NewsBlur endpoint, batch sizes, and feature flags
- Configuration includes rate limiting, backoff settings, and task enablement flags

### Build Process
- **Docker Build**: `bash build.sh` -- builds Docker image tagged with git commit hash
  - Takes 5-15 minutes depending on network connectivity. NEVER CANCEL. Set timeout to 30+ minutes.
  - **Common failure**: Network connectivity issues during pip install phase with "Read timed out" errors
  - **Retry strategy**: Re-run build command if network timeouts occur
  - Image uses `python:3-slim-bullseye` base with working directory `/workspace`

### Running the Application
- **Local development**: `source .env/bin/activate && python src/app.py`
  - Requires NewsBlur credentials (`NB_USERNAME`, `NB_PASSWORD`) in secrets directory or environment
  - App will fail to start without valid credentials but will create database tables first
  - Runs continuous loop with scheduled tasks every hour
- **Production deployment**: `bash container.sh` -- deploys via Docker Swarm using `src/docker-compose.yml`
- **Background process**: Use `bash run.sh` -- runs app in background with logging to `logs/` directory

### Python Code Validation
- **Syntax check**: `python -m py_compile src/app.py` -- validates main application
- **All files**: `find . -name "*.py" -exec python3 -m py_compile {} \;` -- compiles all Python files
- Code compiles successfully on Python 3.12+

## Validation and Testing

### Manual Validation Requirements
After making changes, ALWAYS perform these validation steps:

#### Complete Environment Setup Validation
1. **Fresh environment test**: Start from clean directory without `.env` folder
2. **Virtual environment**: `python3 -m venv .env` -- should complete without errors
3. **Activation**: `source .env/bin/activate` -- prompt should show `(.env)`
4. **Dependencies**: `pip install -r src/requirements.txt` -- may take multiple attempts due to network
5. **Configuration**: `python src/set_defaults.py` -- should create `nb.sqlite` and show config logging
6. **Database verification**: `ls -la nb.sqlite` -- file should exist (36-40KB size)

#### Code Quality Validation
1. **Syntax check**: `python -m py_compile src/app.py` -- no output means success
2. **All files**: `find . -name "*.py" -exec python3 -m py_compile {} \;` -- warnings from dependencies are normal
3. **Import test**: `python -c "import src.app"` -- should fail with missing secrets (expected)

#### Application Startup Validation
1. **Database setup**: `python src/app.py` should log:
   - "Started" message
   - "Executed table creation query" 
   - "Running scheduled update hash list task"
   - Fail with missing secrets error (this is expected and correct)
2. **Timeout test**: Use `timeout 5` to limit runtime since app runs continuously
3. **Database tables**: Verify SQLite database contains `config`, `stories`, `domains`, `story_hashes` tables

### Expected Behavior Validation
- Application logs "Started" and creates SQLite database
- Configuration shows NewsBlur endpoint (https://newsblur.com) and proper task settings
- App attempts to connect to NewsBlur API (requires credentials)
- Datadog warnings about hostname resolution are normal in development environment

### Build Time Expectations
- **NEVER CANCEL**: Virtual environment setup: 1-3 minutes
- **NEVER CANCEL**: Dependency installation: 30 seconds to 5 minutes (network dependent). Set timeout to 15+ minutes.
- **NEVER CANCEL**: Docker build: 5-15 minutes (network dependent). Set timeout to 30+ minutes.
- Configuration setup: under 1 second
- Python compilation check: 15-30 seconds for all files
- Application startup to error: 1-2 seconds (normal with missing credentials)
- **Network-dependent operations**: All pip and Docker operations may experience timeouts requiring retries

## Common Issues and Troubleshooting

### Network Connectivity Issues
- **pip timeouts**: `ReadTimeoutError: HTTPSConnectionPool(host='pypi.org', port=443): Read timed out`
  - **Solution**: Retry the pip command, possibly multiple times
  - **Workaround**: Use `pip install --timeout 1000` for longer timeout
- **Docker build failures**: "Temporary failure in name resolution" during pip install
  - **Solution**: Retry `bash build.sh` command  
  - **Alternative**: Use local Python environment instead of Docker for development

### Missing Credentials (Expected Behavior)
- **Secret file error**: `FileNotFoundError: [Errno 2] No such file or directory: './secrets/NB_USERNAME'`
  - **Status**: This is normal for development environment without NewsBlur credentials
  - **Validation**: App should log "Started" and create database tables before this error
  - **Production**: Requires actual NewsBlur username/password in `./secrets/` directory

### Database and Configuration
- **SQLite location**: Database created as `./nb.sqlite` in project root (not in src/)
- **Size verification**: Fresh database should be 36-40KB after initial setup
- **Configuration verification**: Run `python src/set_defaults.py` to see full config output
- **Table verification**: Database contains: config, stories, domains, story_hashes tables

### Datadog Warnings (Normal)
- **Warning**: `Error submitting packet: [Errno -5] No address associated with hostname`
  - **Status**: Normal in development environment without Datadog agent
  - **Impact**: Does not affect application functionality
  - **Production**: Requires Datadog agent running at `dd_agent` hostname

## Key Application Components

### Main Entry Point
- `src/app.py` -- main application with scheduled task orchestration
- Runs continuous loop with hourly tasks for updating hashes, populating stories, adding comment counts
- Daily task for pruning starred stories at 23:00

### Core Tasks (src/tasks/)
- `populate.py` -- fetches story details from NewsBlur API and stores in database
- `add_comment_counts.py` -- updates comment counts for stories
- `add_domains.py` -- extracts and stores domain information from story URLs
- `prune.py` -- removes starred stories below comment threshold
- `update_comment_counts.py` -- updates existing comment counts

### Database Connectors (src/connectors/)
- `SqliteClient.py` -- default SQLite database client (used by default)
- `PostgresClient.py`, `MySqlClient.py`, `DynamoDbClient.py` -- alternative database backends
- `NewsblurConnector.py` -- API client for NewsBlur with rate limiting and backoff

### Utilities (src/utility/)
- `client_factory.py` -- factory for database and NewsBlur clients
- `nb_logging.py` -- logging configuration
- `NbConfig.py` -- configuration management with sensible defaults

## Development Workflow

### Standard Development Process
1. **Always activate virtual environment first**: `source .env/bin/activate`
2. **Test configuration setup**: `python src/set_defaults.py` -- should complete in under 1 second
3. **Validate syntax**: `find . -name "*.py" -exec python3 -m py_compile {} \;` -- takes 15-30 seconds
4. **Test application startup**: `timeout 5 python src/app.py` -- should show initialization logs then fail on secrets
5. **For Docker changes**: Test complete build process: `bash build.sh` with 30+ minute timeout

### Testing Individual Components
- **Database client**: `python -c "import sys; sys.path.append('src'); from utility import client_factory; print('DB client works:', type(client_factory.get_db_client()))"`
- **Configuration**: `python -c "import sys; sys.path.append('src'); from utility.NbConfig import NbConfig; print('Config keys:', len(NbConfig({}).config))"`
- **Logging setup**: `python -c "import sys; sys.path.append('src'); from utility import nb_logging; nb_logging.setup_logger('test')"`
- **Task modules**: Each task in `src/tasks/` can be imported and tested individually (run from src/ directory)

### Pre-commit Validation Checklist
- [ ] Virtual environment activates: `source .env/bin/activate`
- [ ] Dependencies install: `pip install -r src/requirements.txt`
- [ ] Configuration works: `python src/set_defaults.py`
- [ ] Code compiles: `find . -name "*.py" -exec python3 -m py_compile {} \;`
- [ ] App initializes: `timeout 5 python src/app.py` shows proper startup logs
- [ ] Database created: `ls -la nb.sqlite` shows file exists

## CI/CD Information
- Legacy GitHub Actions workflow in `main.workflow` (HCL format) for Docker builds on releases
- CircleCI configuration minimal (`.circleci/config.yml`) - basic Ruby container, not actively used
- Release process via `release.sh` creates git tags with format `v0.0.1-{git-hash}`
- No existing test framework, linting tools, or automated quality checks configured
- Manual validation is the primary quality assurance method

## Performance and Monitoring
- **Application monitoring**: Uses Datadog for metrics (requires `dd_agent` hostname in production)
- **Error tracking**: Rollbar integration for exception reporting (API key: `00b402fc0da54ed1af8687d4c4389911`)
- **Rate limiting**: Built-in backoff mechanisms for NewsBlur API calls (exponential backoff, configurable)
- **Database performance**: Uses SQLite by default, supports connection pooling for other backends
- **Memory usage**: Processes batches of 10 stories by default (configurable via `BATCH_SIZE`)

## Security Considerations
- **Secrets management**: Expects credentials in `./secrets/` directory, not environment variables
- **API credentials**: Requires NewsBlur username/password for production operation
- **Database access**: SQLite file permissions should be restricted in production
- **Rollbar API key**: Currently hardcoded in `src/app.py` (line 14)