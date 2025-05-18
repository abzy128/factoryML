# FactoryML

Project made as diploma work for the subject of Machine Learning at the Astana IT University.

Title: Development of Predictive Models for Downtime Prevention in Industrial Equipment Machine Learning

# Table of Contents
- [FactoryML](#factoryml)
- [Table of Contents](#table-of-contents)
- [Installation](#installation)
  - [Prerequisites](#prerequisites)
  - [Steps](#steps)
  - [Docker (experimental)](#docker-experimental)
- [Usage](#usage)
- [Technologies Used](#technologies-used)

# Installation

## Prerequisites

- PC with NVIDIA GPU
- Linux
- Docker & Docker Compose
- Yarn (for frontend)
- Node.js (for frontend)
- uv (for backend and other services)
- Python 3.11
- Git

## Steps

Run following commands in the terminal.

1. Clone the repository:
   
```bash
git clone https://github.com/abzy128/factoryML.git
cd factoryML
```

2. Perform initial startup of TimescaleDB:
   
```bash
docker compose up timescale
```

If everything is ok, you can stop the container with `Ctrl + C`.

3. Run all projets

```bash
./run_all.sh
```

This downloads all necessary packages with uv and run the backend and frontend.


## Docker (experimental)

There is configured docker compose for all services, but it does not support GPU yet.
You can run the following command to try it out:

```bash
docker compose up -d
```

# Usage

Open the browser and go to `http://localhost:3000` to see the frontend.

You can see prediction result and values from digital twin by selecting sensor, start and end date parameters.

You can also see Swagger API documentation of services in their respective locations:

| Service      | Url                        |
|--------------|----------------------------|
| Backend      | http://localhost:8001/docs |
| Digital Twin | http://localhost:8002/docs |
| ML inference | http://localhost:8003/docs |

# Technologies Used

ML Model:

- Python
- Pandas
- Keras/Tensorflow
- Scikit-learn
- Jupyter Notebook
- Matplotlib

Backend:
- FastAPI
- PostgreSQL
- TimescaleDB
- Swagger
- Docker
- Docker Compose

Frontend:
- React
- TypeScript
- Tailwind CSS
- Next.js
- shadcn/ui
  