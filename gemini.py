"""
Simple Google Gemini API test for job analysis.
"""

# --- Original Gemini-based implementation (commented out) ---
"""
import os
import json
import requests
from pathlib import Path

# Set your Google API key here or in environment
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', "AIzaSyC94GrLnk9Rm6-bzOx_i_Y42aEP3gjI5i4")

# File path for jobs to filter
JOBS_TO_FILTER_FILE = Path("jobs_to_filter.json")
FILTERED_JOBS_FILE = Path("filtered_jobs.json")

def load_jobs_to_filter():
    """Load jobs from jobs_to_filter.json file."""
    if not JOBS_TO_FILTER_FILE.exists():
        print(f"❌ Jobs file not found: {JOBS_TO_FILTER_FILE}")
        return []
    
    try:
        with open(JOBS_TO_FILTER_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
        
        # Parse as JSON if possible, otherwise return empty list
        jobs_data = json.loads(content)
        return jobs_data if isinstance(jobs_data, list) else []
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in jobs file: {e}")
        return []
    except Exception as e:
        print(f"❌ Error reading jobs file: {e}")
        return []

# Available Gemini models (ordered by rate limit - highest first)
GEMINI_MODELS = [
    'gemini-2.5-pro',             # 5 RPM, 250K tokens
    'gemini-2.5-flash',          # 10 RPM, 250K tokens
    'gemini-2.0-flash',          # 15 RPM, 1M tokens
    'gemini-2.5-flash-lite',     # 15 RPM, 250K tokens  
    'gemini-2.0-flash-lite'     # 30 RPM, 1M tokens
]

def test_gemini_with_retry(model_name, prompt):
    """Test Gemini API with a specific model and retry logic."""
    import time
    
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GOOGLE_API_KEY}'
    
    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }]
    }
    
    headers = {'Content-Type': 'application/json'}

    for attempt in range(3):  # 6 retry attempts
        try:
            print(f"   Attempt {attempt + 1} with {model_name}...")
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                text_response = result['candidates'][0]['content']['parts'][0]['text']
                
                # Remove first and last lines (markdown code blocks)
                lines = text_response.strip().split('\n')
                if len(lines) > 2:
                    lines = lines[1:-1]  # Remove first and last line
                    text_response = '\n'.join(lines)
                
                return True, text_response
            elif response.status_code == 503:
                print(f"   ⏳ Model {model_name} overloaded, waiting 5 seconds...")
                time.sleep(5)
                continue
            else:
                print(f"   ❌ Error {response.status_code}: {response.text}")
                return False, None
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            if attempt < 2:  # Don't sleep on last attempt
                time.sleep(2)
    
    return False, None

def test_gemini_simple():
    """Test a simple request to Gemini API with model fallback."""
    
    prompt = "Hello! Can you respond with a simple JSON object containing: {\"message\": \"Hello from Gemini!\", \"status\": \"success\"}?"
    
    print("🚀 Testing Gemini API...")
    
    # Try each model until one works
    for model in GEMINI_MODELS:
        print(f"🔄 Trying model: {model}")
        success, response = test_gemini_with_retry(model, prompt)
        
        if success:
            print(f"✅ Success with {model}!")
            print(f"✅ Response: {response}")
            return True
        else:
            print(f"❌ Failed with {model}")
    
    print("❌ All models failed!")
    return False

def test_job_analysis():
    """Test job analysis with sample data."""
    
    # Sample job for analysis
    sample_job = {
        "title": "Senior DevOps Engineer",
        "company": "Netflix",
        "location": "Amsterdam, Netherlands"
    }
    
    prompt = f"""
Analyze this job for a DevOps professional with Docker/Kubernetes skills:

Job: {json.dumps(sample_job, indent=2)}

Respond with ONLY this JSON format:
{{
    "relevance_score": <1-10>,
    "is_relevant": <true/false>,
    "reasoning": "<brief explanation>"
}}
"""
    
    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }]
    }
    
    print("\n🔍 Testing job analysis...")
    
    # Try each model until one works  
    for model in GEMINI_MODELS:
        print(f"🔄 Trying job analysis with: {model}")
        success, response = test_gemini_with_retry(model, prompt)
        
        if success:
            print(f"✅ Analysis: {response}")
            
            # Try to parse as JSON
            try:
                analysis = json.loads(response.strip())
                print(f"📊 Score: {analysis.get('relevance_score', 'N/A')}/10")
                print(f"🎯 Relevant: {analysis.get('is_relevant', 'N/A')}")
                return
            except:
                print("⚠️  Response not valid JSON")
                return
        else:
            print(f"❌ Failed with {model}")
    
    print("❌ All models failed for job analysis!")

def batch_job_analysis(jobs):
    """Test batch job analysis with multiple jobs."""
    print("\n🔍 Testing batch job analysis...")

    prompt = f'''Analyze these {len(jobs)} jobs for a DevOps/platform engineer/cloud engineer/sre/infrastructure engineer/production engineer or anything that a devops can work in - professional with Docker/Kubernetes/AWS/Cloud/gitops(Argocd),iac terraform,ci/cd and more,helm charts and and (exclude jobs /lower score on jobs that are heavy on networking or finops since its not my strong side also exclude any software engineering roles or full-stack roles or any Software Engineering (with potential for DevOps) / Software Engineering (Backend/DevOps potential) skills:

Jobs to analyze:
{json.dumps(jobs, indent=2)}

For each job, respond with ONLY this JSON format:
{{
    "results": [
        {{
            "job_title": <job title>,
            "company": <company>,
            "location": <location>,
            "location": <location>,
            "link": <job link>,
            "job_id": <job id>,
            "score": <1-10>,
            "relevant": <true/false>,
            "category": "<job category>",
            "reason": "<brief explanation>"
        }}
    ],
    "summary": {{
        "total_jobs": {len(jobs)},
        "relevant_count": <number of relevant jobs>
    }}
}}
'''

    # Try each model until one works
    for model in GEMINI_MODELS:
        print(f"🔄 Trying batch analysis with: {model}")
        success, response = test_gemini_with_retry(model, prompt)

        if success:
            print(f"✅ Batch Analysis Response:")
            print(response)

            try:
                analysis = json.loads(response.strip())

                print(f"\n📊 Batch Results:")
                print(f"   Total Jobs: {analysis.get('summary', {}).get('total_jobs', 'N/A')}")
                print(f"   Relevant: {analysis.get('summary', {}).get('relevant_count', 'N/A')}")

                print(f"\n🎯 Individual Scores:")
                for result in analysis.get('results', []):
                    job_id = result.get('job_id', 'N/A')
                    score = result.get('score', 'N/A')
                    relevant = result.get('relevant', 'N/A')
                    category = result.get('category', 'N/A')
                    print(f"   Job {job_id}: {score}/10 - {relevant} ({category})")
                
                return response
            except Exception as e:
                print(f"⚠️  JSON parsing error: {e}")
                return response
        else:
            print(f"❌ Failed with {model}")
    
    print("❌ All models failed for batch job analysis!")


if test_gemini_simple():
    # Load jobs from file
    jobs_to_filter = load_jobs_to_filter()
    if jobs_to_filter:
        print(f"📝 Loaded {len(jobs_to_filter)} jobs for AI analysis")
        jobs = batch_job_analysis(jobs_to_filter)
    else:
        print("❌ No jobs loaded - creating empty results")
        jobs = {
            "results": [],
            "summary": {
                "total_jobs": 0,
                "relevant_count": 0
            }
        }
    
    # Always write jobs to file as proper JSON (even if empty)
    with open(FILTERED_JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Results written to {FILTERED_JOBS_FILE}")
else:
    # If Gemini API fails, still create empty results file
    print("❌ Gemini API test failed - creating empty results")
    empty_results = {
        "results": [],
        "summary": {
            "total_jobs": 0,
            "relevant_count": 0
        }
    }
    with open(FILTERED_JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(empty_results, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Empty results written to {FILTERED_JOBS_FILE}")
"""

import json
import re
from pathlib import Path
from urllib.parse import urlparse

JOBS_TO_FILTER_FILE = Path("jobs_to_filter.json")
FILTERED_JOBS_FILE = Path("filtered_jobs.json")


def load_jobs() -> list:
    if not JOBS_TO_FILTER_FILE.exists():
        print(f"❌ Jobs file not found: {JOBS_TO_FILTER_FILE}")
        return []

    try:
        with open(JOBS_TO_FILTER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception as exc:
        print(f"❌ Failed to load jobs: {exc}")
        return []


def extract_job_id(url: str | None) -> str:
    if not url:
        return ""

    match = re.search(r"/jobs/view/[^/-]*-?(\d+)", url)
    if match:
        return match.group(1)

    path = urlparse(url).path
    fallback = re.search(r"(\d{7,})", path)
    if fallback:
        return fallback.group(1)

    return url


def transform_jobs(jobs: list) -> dict:
    results = []

    for entry in jobs:
        job_data = entry.get("job", {}) if isinstance(entry, dict) else {}

        job_title = job_data.get("title") or entry.get("title") or ""
        company = job_data.get("company") or entry.get("company") or ""
        location = job_data.get("location") or entry.get("location") or ""
        link = job_data.get("url") or entry.get("url") or ""
        job_id = extract_job_id(link)

        results.append(
            {
                "job_title": job_title,
                "company": company,
                "location": location,
                "link": link,
                "job_id": job_id,
            }
        )

    return {
        "results": results,
        "summary": {
            "total_jobs": len(results),
        },
    }


def write_results(payload: dict) -> None:
    with open(FILTERED_JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def main() -> None:
    jobs = load_jobs()
    transformed = transform_jobs(jobs)
    write_results(transformed)
    print(f"✅ Wrote {transformed['summary']['total_jobs']} jobs to {FILTERED_JOBS_FILE}")


if __name__ == "__main__":
    main()