# Weather Data ETL pipeline in Airflow

#### Importing Dependencies

```bash
#DAG - defines the workflow
from airflow import DAG

#HttpHook - Helps connect and fetch data from HTTP APIs (here, the weather API).
from airflow.providers.http.hooks.http import HttpHook

#PostgresHook - Helps connect to PostgreSQL databases.
from airflow.providers.postgres.hooks.postgres import PostgresHook

#@task → Airflow’s TaskFlow API decorator, makes Python functions into Airflow tasks.
from airflow.decorators import task

#days_ago → Utility to set start_date relative to today.
from airflow.utils.dates import days_ago
```

# Airflow Tasks
#### 1.**Extract Data**
- Connects to the weather API using `HttpHook`.
- Calls the endpoint `/v1/forecast?....`
- Returns JSON response → raw weather data (all timestamps & hourly temperatures)

#### 2.**Transform Data**
- Extracts the current_weather portion of the API response.
- Creates a simplified dictionary containing:
    - temperature
    - windspeed
    - winddirection
    - weathercode
    - Latitude and longitude

#### 3.**Load Data**
- Connects to PostgreSQL using a PostgresHook.
- Inserts the transformed weather data into the weather_data table.
- Ensures no duplicates using ON CONFLICT (timestamp) DO NOTHING.

# docker-compose.yml
What is Docker Compose?
- Docker Compose is a tool to define and run multi-container Docker applications.
- Instead of running each Docker container manually, you write a single YAML file (docker-compose.yml) that describes all the containers and how they interact.
- Then you can start all containers with one command.
- Makes managing multiple containers easier. Example: Airflow project needs:
    - Airflow container → runs DAGs and webserver
    - Postgres container → stores your data


+-----------------+        docker network       +----------------+
|  Airflow        |  ------------------------> | Postgres       |
|  Container      |                             | Container      |
|  (DAG runs)     |                             | (Database)     |
+-----------------+                             +----------------+

Docker Container
- When you define a Postgres service in Docker Compose, Docker creates a Postgres container.

- That container is like a mini virtual machine running Postgres, isolated from your OS.

- Airflow (in its own container) connects to this Postgres container over Docker’s internal network.

- All your ETL data gets stored inside this Postgres container (or in a Docker volume if you’ve defined one for persistence).


Airflow Container
- Airflow has many dependencies (Python, Airflow packages, providers, etc.).

- Running it in a container isolates it from your OS, so you don’t have conflicts.

- Docker ensures your Airflow environment is exactly the same on any machine.


What’s inside the Airflow container

When you run Airflow in Docker (via Astronomer or docker-compose), the container typically includes:

1. Webserver

- Provides the Airflow UI (http://localhost:8080)
- Lets you view DAGs, trigger tasks, check logs

2. Scheduler
- Continuously monitors your DAGs
- Determines which tasks need to run and when

3. Task Executor
- Runs the actual Python code for your DAGs
- In a simple setup, this is the LocalExecutor (tasks run inside the same container)

4. DAGs folder (mounted from your local machine)
- Airflow reads all DAGs from here automatically

5. Logs folder
- Stores logs for every task execution

**Interaction Diagram**

+-----------------+       docker network        +----------------+
|  Airflow        |  ------------------------> | Postgres       |
|  Container      |                              | Container      |
|  - Webserver    |                              | - Database     |
|  - Scheduler    |                              |                |
|  - Executor     |                              |                |
|  - DAGs Folder  |                              |                |
+-----------------+                              +----------------+
         |
         | DAG triggers tasks (extract, transform, load)
         v
    Your Python code runs inside the Airflow container

# Weather ETL Pipeline Docker Setup – Step by Step

## **Traditional Docker Compose**
- You define it manually (`image: apache/airflow:...`)
- You define `postgres` service manually
- Volumes & DAGs mounting, Manual (`./dags:/opt/airflow/dags`)
- running `docker-compose up -d`
- environment var, Set manually in `docker-compose.yml`

below steps mention the traditional docker compose.

**Step 1: Specify Docker Compose version**
- Defines the Docker Compose file format.
- Version 3.8 is compatible with modern Docker installations.

**Step 2: Define Services**
- Every container is defined under services:.
- Our project needs two containers:
    1. Postgres: Database for ETL data and Airflow metadata
    2. Airflow: Runs the DAGs, webserver, and scheduler

**Step 3: Define the Postgres service**
Explanation:
- `image`: Postgres version 15
- `container_name`: Name of the Postgres container
- `environment`: Set `username`, `password`, and `database_name`
- `ports`: Expose container port to host machine (optional, useful for pgAdmin)
- `volumes`: Persist Postgres data outside the container (so it’s not lost when container stops)

**Step 4: Define the Airflow service**
- `image`: Official Airflow Docker image
- `depends_on`: Ensure Postgres starts before Airflow
- `AIRFLOW__CORE__EXECUTOR`:Run tasks locally in the container
- `AIRFLOW__CORE__SQL_ALCHEMY_CONN`:Connection string to Postgres container
```bash
postgresql+psycopg2://<user>:<password>@<host>:<port>/<database>
```
- `AIRFLOW__CORE__LOAD_EXAMPLES`: Don’t load example DAGs
- `volumes`: Mount local DAGs folder and requirements file
- `ports`: Expose Airflow UI on localhost:8080
- `command`: Start Airflow webserver


**If you’re using Astronomer CLI to run your DAG locally, the docker-compose.yml is slightly different, because Astronomer provides its own Docker setup under the hood. You usually don’t write the full Airflow service manually**

## **Using Astronomer CLI**

With Astronomer:
- Airflow container is handled automatically, so you don’t define it manually.
- You only need to define supporting services (like Postgres).
- DAGs, Python dependencies, and environment variables are mounted automatically by Astronomer.
- Astronomer manages Airflow container automatically
- Astronomer can create a Postgres container if needed, or use your own
- Astronomer mounts your dags/ folder automatically
- running, `astro dev start` (handles building, running Airflow, scheduler, webserver)
- Set in `.env` file or via `Dockerfile` / `astro dev start`


## Environment Variables (.env):
- Stores credentials for PostgreSQL and Airflow.
- Keeps sensitive data out of code.
- Example variables: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT` 

## Airflow Connections:
- PostgreSQL: Host = etl-weather_501598-postgres-1, Port = 5433, DB = weather_db, User = thimira.
- HTTP: Base URL = https://api.open-meteo.com.

## Key points:
- Fully containerized; runs consistently anywhere.
- Credentials stored in .env (not committed to GitHub).
- Airflow handles scheduling, monitoring, and logging.