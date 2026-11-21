<div align="center">

# 🎬 Movie Recommendation System

### A Hybrid Movie Recommendation Engine Built with Python & Machine Learning

Discover movies you'll love with a hybrid recommendation system combining collaborative filtering, content-based filtering, and popularity-based ranking.

<br>

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-Backend-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![NumPy](https://img.shields.io/badge/NumPy-013243?logo=numpy&logoColor=white)](https://numpy.org/)
[![Pandas](https://img.shields.io/badge/Pandas-150458?logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![JavaScript](https://img.shields.io/badge/JavaScript-ES6+-F7DF1E?logo=javascript&logoColor=black)](https://developer.mozilla.org/en-US/docs/Web/JavaScript)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

<br>

[![Live Demo](https://img.shields.io/badge/Live-Demo-success?style=for-the-badge&logo=vercel)](https://movie-recommender-sooty.vercel.app/)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-181717?style=for-the-badge&logo=github)](https://github.com/manishyadav-aiml/movie-recommender)

<br>

### 🚀 [TRY THE LIVE APPLICATION](https://movie-recommender-sooty.vercel.app/)

</div>

---

## 📌 Table of Contents

1. [Overview](#-overview)
2. [Project Objectives](#-project-objectives)
3. [Key Features](#-key-features)
4. [Application Architecture](#-application-architecture)
5. [Machine Learning Methodology](#-machine-learning-methodology)
6. [Model Evaluation](#-model-evaluation)
7. [Technology Stack](#-technology-stack)
8. [Project Structure](#-project-structure)
9. [Installation and Setup](#-installation-and-setup)
10. [Running the Application](#-running-the-application)
11. [Running Tests](#-running-tests)
12. [Docker Deployment](#-docker-deployment)
13. [Vercel Deployment](#-vercel-deployment)
14. [Dataset](#-dataset)
15. [Security](#-security)
16. [Limitations and Future Improvements](#-limitations-and-future-improvements)
17. [Author](#-author)
18. [License and Attribution](#-license-and-attribution)

---

## 📖 Overview

The **Movie Recommendation System** is a machine learning-based web application that helps users discover movies based on movie characteristics, historical user ratings, and preference patterns.

The application implements a **Hybrid Recommendation System** combining three recommendation techniques:

- Item-Based Collaborative Filtering
- Content-Based Filtering
- Popularity-Based Recommendation

By combining these approaches, the system generates ranked movie recommendations using multiple sources of information rather than relying on a single algorithm.

The project includes:

- A responsive Flask web application.
- A machine learning recommendation engine.
- A command-line recommendation interface.
- A Streamlit application.
- Offline model evaluation.
- Automated testing.
- Cloud deployment using Vercel.

### 🌐 Live Application

The application is publicly deployed and accessible here:

**[https://movie-recommender-sooty.vercel.app/](https://movie-recommender-sooty.vercel.app/)**

**GitHub Repository:**  
https://github.com/manishyadav-aiml/movie-recommender

---

## 🎯 Project Objectives

The main objectives of this project are:

- Develop a practical movie recommendation system using machine learning.
- Understand and implement collaborative filtering.
- Implement content-based movie similarity.
- Combine different recommendation techniques into a hybrid model.
- Improve recommendation relevance through score-based ranking.
- Evaluate model performance using recommendation metrics.
- Build a responsive and user-friendly web application.
- Develop reusable backend and recommendation components.
- Deploy the application for public access.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🔎 Movie Search | Search movies using live suggestions and typo-tolerant matching. |
| 🎬 Similar Movies | Discover movies related to a selected movie. |
| ⭐ Personalized Recommendations | Create a browser-stored preference profile using movie ratings. |
| 🏆 Top-Rated Movies | Explore movies using weighted rating calculations. |
| 🎭 Genre Filtering | Filter recommendations by movie genre. |
| 📊 Recommendation Scores | Display similarity scores and recommendation explanations. |
| 🔍 Search Suggestions | Receive suggestions while typing movie titles. |
| 🌙 Dark Mode | Switch between light and dark themes. |
| 📱 Responsive Interface | Access the application across desktop and mobile screens. |
| 🖥️ CLI Support | Generate recommendations through the terminal. |
| 📈 Model Evaluation | Evaluate recommendation performance using ranking metrics. |
| 🌐 Cloud Deployment | Access the application through a public Vercel deployment. |

---

## 🏗️ Application Architecture

The application follows a modular architecture that separates the web interface, recommendation logic, data processing, and evaluation components.

### System Architecture

```text
                   USER
                    |
                    v
             WEB INTERFACE
                    |
                    v
             FLASK APPLICATION
                    |
                    v
          RECOMMENDATION ENGINE
                    |
          +---------+---------+
          |         |         |
          v         v         v
     COLLABORATIVE CONTENT  POPULARITY
      FILTERING  FILTERING   MODEL
          |         |         |
          +---------+---------+
                    |
                    v
              HYBRID RANKING
                    |
                    v
            RECOMMENDED MOVIES
```

### Recommendation Workflow

1. Load the processed MovieLens dataset.
2. Prepare movie and rating information.
3. Calculate item-based collaborative similarities.
4. Generate content-based similarity scores.
5. Calculate popularity-based scores.
6. Combine recommendation signals.
7. Rank movies using the hybrid scoring method.
8. Return recommendations to the application.

---

## 🧠 Machine Learning Methodology

The project uses three recommendation techniques to generate movie recommendations.

### 1. Item-Based Collaborative Filtering

Collaborative filtering identifies relationships between movies using historical user-rating patterns.

The implementation includes:

- User rating mean-centering.
- Movie-to-movie similarity calculation.
- Cosine similarity.
- Similarity shrinkage.
- Recommendation ranking using historical ratings.

The system identifies movies that receive similar rating patterns from users.

### 2. Content-Based Filtering

Content-based filtering recommends movies based on their characteristics.

The project uses:

- Movie genres.
- Release decades.
- TF-IDF-style feature representation.
- NumPy-based similarity calculations.

This recommendation component provides an additional signal based on movie metadata.

### 3. Popularity-Based Recommendation

The popularity model uses Bayesian weighted ratings.

This approach considers both the average rating and the number of ratings received by a movie.

It helps prevent movies with very few ratings from automatically ranking above movies with more consistent rating histories.

### 4. Hybrid Recommendation Model

The final recommendation score combines the outputs of all three approaches.

**Hybrid Recommendation Formula:**

```text
Hybrid Score =

0.70 × Collaborative Filtering Score
+
0.25 × Content-Based Score
+
0.05 × Popularity Score
```

Each component is min-max scaled before combination.

The model weights were tuned on one random split and evaluated on a separate split.

### Why a Hybrid Model?

| Recommendation Technique | Main Advantage |
|---|---|
| Collaborative Filtering | Learns relationships from user-rating patterns. |
| Content-Based Filtering | Identifies similarity using movie characteristics. |
| Popularity-Based Filtering | Provides a popularity-oriented recommendation signal. |
| Hybrid Recommendation | Combines multiple recommendation signals. |

---

## 📊 Model Evaluation

The recommendation models were evaluated using the **MovieLens ml-1m dataset**.

### Evaluation Configuration

| Parameter | Configuration |
|---|---|
| Dataset | MovieLens ml-1m |
| Test Users | 600 |
| Recommendation Count | Top 10 |
| Test Split | 20% of each selected user's ratings |
| Relevant Rating | Rating >= 4 |
| Evaluation Type | Offline Evaluation |

### Evaluation Metrics

**Precision@10**

Measures the proportion of recommended movies that are relevant.

**Recall@10**

Measures the proportion of relevant movies successfully recommended.

**Hit Rate@10**

Measures how often at least one relevant movie appears in the recommendations.

**NDCG@10**

Evaluates recommendation ranking quality, giving greater importance to relevant movies appearing near the top.

### Model Comparison

| Model | Precision@10 | Recall@10 | Hit Rate@10 | NDCG@10 |
|---|---:|---:|---:|---:|
| Popularity Baseline | 0.079 | 0.043 | 0.442 | 0.093 |
| Content Only | 0.037 | 0.027 | 0.250 | 0.043 |
| Collaborative Filtering Only | 0.183 | 0.106 | 0.688 | 0.221 |
| **Hybrid Model** | **0.209** | **0.135** | **0.760** | **0.256** |

### Key Results

The hybrid recommendation model achieved:

- **Precision@10:** 0.209
- **Recall@10:** 0.135
- **Hit Rate@10:** 0.760
- **NDCG@10:** 0.256

The hybrid model achieved approximately **2.75 times the NDCG@10 of the popularity baseline** under this evaluation setup.

### Reproduce Model Evaluation

Run the following command:

```bash
python -m scripts.evaluate --dataset ml-1m
```

> These are offline evaluation results from the specified experimental setup. Results may vary with different datasets, users, and evaluation splits.

---

## 🛠️ Technology Stack

| Category | Technologies |
|---|---|
| Programming Language | Python 3.12 |
| Data Processing | NumPy, Pandas |
| Machine Learning | Collaborative Filtering, Content-Based Filtering |
| Similarity Calculation | Cosine Similarity |
| Backend | Flask |
| Frontend | HTML5, CSS3, JavaScript |
| Database | SQLite |
| Alternative Interface | Streamlit |
| Testing | Pytest |
| Deployment | Vercel |
| CI/CD | GitHub Actions |
| Containerization | Docker |
| Version Control | Git, GitHub |

---

## 📂 Project Structure

```text
movie-recommender/
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── .streamlit/
│
├── api/
│
├── data/
│   └── processed/
│
├── docs/
│
├── instance/
│
├── notebooks/
│   └── eda.ipynb
│
├── results/
│
├── scripts/
│
├── src/
│   ├── data.py
│   ├── models.py
│   ├── recommender.py
│   └── evaluation.py
│
├── tests/
│
├── web/
│   ├── templates/
│   ├── static/
│   ├── app.py
│   ├── db.py
│   └── security.py
│
├── .dockerignore
├── .env.example
├── .gitignore
├── .vercelignore
│
├── cli.py
├── Dockerfile
├── README.md
├── requirements.txt
├── requirements-dev.txt
├── requirements-streamlit.txt
├── server.py
└── streamlit_app.py
```

---

## ⚙️ Installation and Setup

Follow these instructions to run the project locally.

### Prerequisites

Make sure you have installed:

- Python 3.12
- Git
- pip

### Step 1: Clone the Repository

```bash
git clone https://github.com/manishyadav-aiml/movie-recommender.git
```

### Step 2: Navigate to the Project Directory

```bash
cd movie-recommender
```

### Step 3: Create a Virtual Environment

**Windows PowerShell**

```powershell
py -3.12 -m venv .venv
```

**macOS / Linux**

```bash
python3.12 -m venv .venv
```

### Step 4: Activate the Virtual Environment

**Windows PowerShell**

```powershell
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
source .venv/bin/activate
```

### Step 5: Upgrade pip and Install Dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 6: Configure Environment Variables

Copy the example environment file.

**Windows PowerShell**

```powershell
Copy-Item .env.example .env
```

**macOS / Linux**

```bash
cp .env.example .env
```

Configure the environment variables according to your local setup.

Never commit real credentials or production secrets to GitHub.

---

## 🚀 Running the Application

### 1. Run the Flask Web Application

```bash
python server.py
```

Open the application in your browser:

```text
http://127.0.0.1:5000
```

### 2. Run the Command-Line Interface

Example:

```bash
python cli.py "The Matrix" -n 5
```

Example with ratings and genre filtering:

```bash
python cli.py --rate "The Godfather=5" "Heat=4.5" --genre Crime
```

### 3. Run the Streamlit Application

Install the additional dependencies:

```bash
pip install -r requirements-streamlit.txt
```

Start Streamlit:

```bash
streamlit run streamlit_app.py
```

---

## 🧪 Running Tests

The project uses Pytest for automated testing.

### Install Development Dependencies

```bash
pip install -r requirements-dev.txt
```

### Execute the Test Suite

```bash
pytest
```

The tests cover application behaviour, recommendation functionality, security, and other project components.

---

## 🐳 Docker Deployment

The project includes a Dockerfile for containerized execution.

### Build the Docker Image

```bash
docker build -t movie-recommender .
```

### Run the Container

```bash
docker run -p 8000:8000 --env-file .env movie-recommender
```

---

## ☁️ Vercel Deployment

The application is deployed using Vercel.

### 🌐 Live Deployment

**[https://movie-recommender-sooty.vercel.app/](https://movie-recommender-sooty.vercel.app/)**

### Deployment Configuration

1. Push the project to GitHub.
2. Open Vercel.
3. Import the GitHub repository.
4. Configure the project root directory.
5. Configure the required environment variables.
6. Deploy the application.

### Environment Variables

Configure the following variables in Vercel:

| Variable | Value |
|---|---|
| `APP_ENV` | `production` |
| `SECRET_KEY` | Your securely generated secret |

Generate a secure secret locally:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Do not publish the generated secret in your README or GitHub repository.

### Deployment Notes

- The deployment bundle is configured to include the `ml-small` processed dataset.
- Larger datasets are excluded from the Vercel deployment bundle.
- Feedback and the admin inbox are disabled on Vercel by default because serverless function filesystems are not persistent storage.

---

## 📚 Dataset

This project uses the **MovieLens dataset**, provided by GroupLens Research at the University of Minnesota.

### Dataset Source

[MovieLens Datasets](https://grouplens.org/datasets/movielens/)

### Datasets Used

| Dataset | Description |
|---|---|
| `ml-small` | Approximately 100K ratings |
| `ml-1m` | Approximately 1M ratings |
| `ml-25m-top` | Approximately 2M ratings for the 5,000 most-rated movies |

### Dataset Preparation

The project includes data preparation scripts for processing the MovieLens datasets.

Run:

```bash
python -m scripts.prepare_data
```

### Dataset Selection

You can select a dataset using the `MOVIES_DATASET` environment variable.

Example:

```text
MOVIES_DATASET=ml-25m-top
```

Refer to the official MovieLens website for dataset details and usage information.

---

## 🔐 Security

The application includes several security measures:

- Input validation for application endpoints.
- CSRF protection and Origin checks for POST requests.
- Rate limiting.
- Parameterized SQL queries.
- Output escaping.
- Content Security Policy.
- Security-related HTTP response headers.
- Environment-based secret configuration.
- Optional admin area with hashed password.
- Generic error responses to avoid exposing internal details.
- Secret-scanning script included in the CI workflow.

---

## 🔮 Limitations and Future Improvements

The current recommendation system provides a hybrid approach, but several areas can be explored further.

### Planned Improvements

- Integrate movie posters and richer movie metadata.
- Add plot-summary-based content recommendations.
- Experiment with Matrix Factorization, SVD, and ALS.
- Improve cold-start recommendations for new users.
- Improve recommendations for newly released movies.
- Evaluate model performance across additional datasets and data splits.
- Explore advanced personalization techniques.
- Improve recommendation explanations.

---

## 👨‍💻 Author

<div align="center">

### Manish Kumar Yadav

**B.Tech Computer Science and Engineering  
Artificial Intelligence and Machine Learning**

Building projects in Machine Learning, Artificial Intelligence, and Software Development.

<br>

[![GitHub](https://img.shields.io/badge/GitHub-manishyadav--aiml-181717?style=for-the-badge&logo=github)](https://github.com/manishyadav-aiml)

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2?style=for-the-badge&logo=linkedin)](https://www.linkedin.com/in/manishkumaryadav946)

</div>

---

## 📄 License and Attribution

This project is licensed under the **MIT License**.

See the [LICENSE](LICENSE) file for more information.

MovieLens data is provided by GroupLens Research. Refer to the [MovieLens website](https://grouplens.org/datasets/movielens/) for dataset attribution and usage information.

---

<div align="center">

### ⭐ If you find this project useful, consider giving it a star on GitHub!

**Built with Python, Machine Learning, and Flask.**

<br>

[🚀 Live Application](https://movie-recommender-sooty.vercel.app/)

</div>