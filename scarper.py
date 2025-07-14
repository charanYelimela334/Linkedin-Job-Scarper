"""
LinkedIn Job Scraper with Google Sheets Integration

This script scrapes LinkedIn job listings and writes the results
directly to a Google Sheet titled "FLM Daily Job Updates".

Author: [Charan Yelimela]
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import random
import time
from typing import List, Dict, Optional
import datetime
import gspread
from google.oauth2.service_account import Credentials


# 🔐 SETUP: Enter your Google Sheets credentials file name here
GOOGLE_CREDENTIALS_FILE = "creds.json"  # <-- Your downloaded JSON key
GOOGLE_SHEET_NAME = "FLM Daily Job Updates"  # <-- Your target sheet name


def export_to_google_sheets_only(df: pd.DataFrame) -> bool:
    """
    Export job data to Google Sheet and overwrite existing data.
    """
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_FILE, scopes=scope)
        client = gspread.authorize(creds)

        # Open the Google Sheet
        sheet = client.open(GOOGLE_SHEET_NAME)
        worksheet = sheet.sheet1  # or use .worksheet("Sheet1") for specific tab

        worksheet.clear()

        # Prepare data
        rows = [df.columns.tolist()] + df.fillna('').values.tolist()
        worksheet.update(rows)

        print(f"✅ Data exported to Google Sheet: {GOOGLE_SHEET_NAME}")
        return True
    except Exception as e:
        print(f"❌ Google Sheets export failed: {e}")
        return False


def get_user_input() -> tuple[str, str, int, str, str, str]:
    print("=" * 60)
    print("🔍 LinkedIn Job Scraper - Google Sheets Edition")
    print("=" * 60)

    job_title = input("📋 Enter the job role/title: ").strip()
    while not job_title:
        job_title = input("❌ Can't be empty. Enter job title: ").strip()

    job_location = input("📍 Enter the job location: ").strip()
    while not job_location:
        job_location = input("❌ Can't be empty. Enter location: ").strip()

    print("\n🗓️ Date Posted Filter:")
    print("1. Any time\n2. Past month\n3. Past week (default)\n4. Past 24 hours")
    date_filter_map = {"1": "", "2": "r2592000", "3": "r604800", "4": "r86400"}
    date_choice = input("Choose (1-4, default 3): ").strip() or "3"
    date_filter = date_filter_map.get(date_choice, "r604800")

    print("\n🎓 Experience Levels:")
    print("1. Any level (default)\n2. Internship\n3. Entry\n4. Associate\n5. Mid-Senior\n6. Director\n7. Executive")
    exp_filter_map = {"1": "", "2": "1", "3": "2", "4": "3", "5": "4", "6": "5", "7": "6"}
    exp_choice = input("Enter levels (e.g. 3,4 or 'all'): ").strip().lower()

    if exp_choice == "all":
        exp_filter = ",".join([exp_filter_map[str(i)] for i in range(2, 8)])
    elif not exp_choice or exp_choice == "1":
        exp_filter = ""
    else:
        levels = [exp_filter_map.get(l.strip()) for l in exp_choice.split(",") if l.strip() in exp_filter_map]
        exp_filter = ",".join(filter(None, levels))

    max_jobs = input("📊 How many jobs to scrape? (default 25, max 100): ").strip()
    max_jobs = int(max_jobs) if max_jobs and max_jobs.isdigit() else 25

    return job_title, job_location, max_jobs, "FLM Daily Job Updates", date_filter, exp_filter


def fetch_job_ids(title: str, location: str, max_jobs: int, date_filter: str = "", exp_filter: str = "") -> List[str]:
    ids = []
    start = 0
    while len(ids) < max_jobs:
        import urllib.parse
        encoded_title = urllib.parse.quote(title)
        encoded_location = urllib.parse.quote(location)
        url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={encoded_title}&location={encoded_location}&start={start}"
        params = []
        if date_filter:
            params.append(f"f_TPR={date_filter}")
        if exp_filter:
            params.append(f"f_E={exp_filter}")
        if params:
            url += "&" + "&".join(params)
        try:
            resp = requests.get(url)
            if resp.status_code != 200:
                break
            soup = BeautifulSoup(resp.text, "html.parser")
            jobs = soup.find_all("li")
            if not jobs:
                break
            for job in jobs:
                base_card = job.find("div", {"class": "base-card"})
                if base_card and base_card.get("data-entity-urn"):
                    job_id = base_card.get("data-entity-urn").split(":")[3]
                    if job_id not in ids:
                        ids.append(job_id)
                    if len(ids) >= max_jobs:
                        break
            start += 25
            time.sleep(random.uniform(1, 2))
        except requests.RequestException:
            break
    return ids


def fetch_job_details(job_id: str) -> Optional[Dict[str, Optional[str]]]:
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
    try:
        resp = requests.get(url)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        return {
            "job_url": f"https://www.linkedin.com/jobs/view/{job_id}",
            "job_title": soup.find("h2").text.strip() if soup.find("h2") else None,
            "company_name": soup.find("a", {"class": "topcard__org-name-link"}).text.strip() if soup.find("a", {"class": "topcard__org-name-link"}) else None,
            "job_location": soup.find("span", {"class": "topcard__flavor--bullet"}).text.strip() if soup.find("span", {"class": "topcard__flavor--bullet"}) else None,
            "time_posted": soup.find("span", {"class": "posted-time-ago__text"}).text.strip() if soup.find("span", {"class": "posted-time-ago__text"}) else None,
            "num_applicants": soup.find("span", {"class": "num-applicants__caption"}).text.strip() if soup.find("span", {"class": "num-applicants__caption"}) else None,
            "job_description_preview": soup.find("div", {"class": "show-more-less-html__markup"}).text.strip()[:200] if soup.find("div", {"class": "show-more-less-html__markup"}) else None
        }
    except:
        return None


def scrape_linkedin_jobs(title: str, location: str, max_jobs: int, date_filter: str = "", exp_filter: str = "") -> pd.DataFrame:
    print(f"\n🔍 Searching for '{title}' jobs in '{location}'...")
    job_ids = fetch_job_ids(title, location, max_jobs, date_filter, exp_filter)
    if not job_ids:
        print("❌ No job IDs found.")
        return pd.DataFrame()

    print(f"📊 Found {len(job_ids)} job IDs.")
    jobs = []
    for i, job_id in enumerate(job_ids, 1):
        print(f"🔄 [{i}/{len(job_ids)}] Fetching job ID: {job_id}")
        job = fetch_job_details(job_id)
        if job:
            jobs.append(job)
        time.sleep(random.uniform(1, 2))
    return pd.DataFrame(jobs)


def display_and_save_results(df: pd.DataFrame) -> bool:
    if df.empty:
        print("❌ No jobs found.")
        return False
    print("\n🎯 Sample Results:")
    print("=" * 80)
    for i, job in df.head(5).iterrows():
        print(f"\n{i+1}. 📋 {job['job_title'] or 'N/A'}")
        print(f"   🏢 {job['company_name'] or 'N/A'}")
        print(f"   📍 {job['job_location'] or 'N/A'}")
        print(f"   🗓️ {job['time_posted'] or 'N/A'}")
        print(f"   🔗 {job['job_url']}")
    print("=" * 80)
    return export_to_google_sheets_only(df)


def main():
    try:
        job_title, job_location, max_jobs, _, date_filter, exp_filter = get_user_input()
        confirm = input("\n✅ Proceed with scraping? (y/n): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("❌ Cancelled by user.")
            return
        df = scrape_linkedin_jobs(job_title, job_location, max_jobs, date_filter, exp_filter)
        success = display_and_save_results(df)
        if success:
            print("🎉 Job data written to Google Sheets.")
    except KeyboardInterrupt:
        print("⚠️ Interrupted.")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
