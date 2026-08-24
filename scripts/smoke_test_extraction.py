"""
scripts/smoke_test_extraction.py

Live extraction smoke test — makes real Anthropic API calls.
Requires ANTHROPIC_API_KEY and DATABASE_URL in .env (or environment).

Run from the project root:
    python -m scripts.smoke_test_extraction
"""

import asyncio
import json
from dotenv import load_dotenv

load_dotenv()

from src.services.extractor import extract_resume, extract_job_description

SAMPLE_RESUME = """
Priya Rajan
Senior Data Engineer

EXPERIENCE
-----------
Senior Data Engineer | DataStream Inc | Jan 2022 – Present
- Designed and maintained 40+ Airflow DAGs orchestrating petabyte-scale ETL pipelines
- Reduced pipeline latency by 35% by migrating to Apache Spark on EMR
- Led a team of 3 junior engineers

Data Engineer | FinTech Solutions | Jul 2019 – Dec 2021
- Built real-time streaming pipelines using Kafka and Flink
- Developed dbt models for financial reporting; cut report generation time by 60%
- Maintained PostgreSQL and Redshift data warehouses

Junior Data Analyst | RetailCo | Jan 2018 – Jun 2019
- Wrote SQL queries and Python scripts for ad-hoc reporting
- Created Tableau dashboards for the marketing team

EDUCATION
---------
B.Tech Computer Science | Indian Institute of Technology Bombay | 2017

SKILLS
------
Python, SQL, Apache Spark, Apache Kafka, Apache Flink, Airflow, dbt,
AWS (EMR, Redshift, S3, Glue), PostgreSQL, Tableau, Git, Docker
"""

SAMPLE_JD = """
Job Title: Senior Data Engineer
Company: CloudScale Analytics

About the Role:
We're looking for a Senior Data Engineer to join our growing data platform team.
You'll design scalable pipelines that power our ML and analytics products.

Requirements:
- 4+ years of experience in data engineering
- Strong proficiency in Python and SQL (required)
- Experience with Apache Spark or Flink (required)
- Hands-on experience with a cloud data warehouse such as Redshift, BigQuery, or Snowflake (required)
- Experience with workflow orchestration tools like Airflow or Prefect (required)
- Bachelor's degree in Computer Science, Engineering, or a related field

Nice to Have:
- Experience with dbt for data transformation
- Familiarity with streaming frameworks (Kafka, Kinesis)
- Knowledge of Kubernetes or Docker for containerised deployments
- Experience mentoring junior engineers
"""


async def main():
    print("=" * 60)
    print("LIVE EXTRACTION SMOKE TEST")
    print("=" * 60)

    print("\n--- RESUME EXTRACTION ---")
    resume, _ = await extract_resume(SAMPLE_RESUME)
    print(json.dumps(resume.model_dump(), indent=2))

    print("\n--- JOB DESCRIPTION EXTRACTION ---")
    jd = await extract_job_description(SAMPLE_JD)
    print(json.dumps(jd.model_dump(), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
