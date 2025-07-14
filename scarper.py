"""
LinkedIn Job Scraper

A modern, modular Python script to scrape job postings from LinkedIn's public job search API.
Features interactive prompts, robust error handling, and CSV export.

Author: [Your Name]
Date: [Current Date]
Version: 2.0

Dependencies:
- requests
- beautifulsoup4
- pandas
- random
- time

Usage:
    python scarper.py

Note: For educational use. Please respect LinkedIn's Terms of Service.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import random
import time
from typing import List, Dict, Optional
import datetime


def get_user_input() -> tuple[str, str, int, str, str, str]:
    """
    Prompt the user for job search parameters and output filename, plus filters.
    Returns: (job_title, job_location, max_jobs, filename, date_filter, exp_filter)
    """
    print("=" * 60)
    print("           🔍 LinkedIn Job Scraper 🔍")
    print("=" * 60)
    print("Welcome! This tool will help you scrape LinkedIn job postings.")
    print("Please provide the following information:\n")

    job_title = input("📋 Enter the job role/title (e.g., Python Developer): ").strip()
    while not job_title:
        print("❌ Job title cannot be empty!")
        job_title = input("📋 Enter the job role/title: ").strip()

    job_location = input("📍 Enter the job location (e.g., Toronto, Remote): ").strip()
    while not job_location:
        print("❌ Job location cannot be empty!")
        job_location = input("📍 Enter the job location: ").strip()

    # Date posted filter - Set to Past Week by default
    print("\n🗓️ Job Posted Date:")
    print("1. Any time")
    print("2. Past month")
    print("3. Past week (default) ⭐")
    print("4. Past 24 hours")
    date_filter_map = {
        "1": "",           # Any time
        "2": "r2592000",   # Past month (30 days)
        "3": "r604800",    # Past week (7 days)
        "4": "r86400"      # Past 24 hours (1 day)
    }
    while True:
        date_choice = input("Select job posted date filter (1-4, default: 3): ").strip() or "3"
        if date_choice in date_filter_map:
            break
        print("❌ Please enter 1, 2, 3, or 4!")
    date_filter = date_filter_map[date_choice]

    # Experience level filter - Multiple selection support
    print("\n🎓 Experience Level (Multiple Selection):")
    print("1. Any level (default)")
    print("2. Internship")
    print("3. Entry level")
    print("4. Associate")
    print("5. Mid-Senior level")
    print("6. Director")
    print("7. Executive")
    print("\n💡 You can select multiple levels by entering numbers separated by commas (e.g., 2,3,4)")
    print("   Or enter 'all' to select all levels, or press Enter for 'Any level'")
    
    exp_filter_map = {
        "1": "",   # Any level
        "2": "1",  # Internship
        "3": "2",  # Entry level
        "4": "3",  # Associate
        "5": "4",  # Mid-Senior level
        "6": "5",  # Director
        "7": "6"   # Executive
    }
    
    while True:
        exp_choice = input("Select experience level(s) (1-7, comma-separated, 'all', or Enter for any): ").strip()
        
        if not exp_choice:
            exp_filter = ""
            break
        elif exp_choice.lower() == "all":
            # Select all specific levels (2-7)
            exp_filter = ",".join([exp_filter_map[str(i)] for i in range(2, 8)])
            break
        else:
            # Parse comma-separated selections
            try:
                selected_levels = [x.strip() for x in exp_choice.split(",")]
                valid_levels = []
                for level in selected_levels:
                    if level in exp_filter_map:
                        if level == "1":  # "Any level" overrides others
                            valid_levels = [""]
                            break
                        valid_levels.append(exp_filter_map[level])
                    else:
                        print(f"❌ Invalid level '{level}'. Please enter numbers 1-7.")
                        break
                else:
                    if valid_levels:
                        exp_filter = ",".join(valid_levels)
                        break
                    else:
                        print("❌ Please select at least one valid level!")
            except Exception:
                print("❌ Invalid input. Please enter numbers separated by commas.")

    while True:
        max_jobs_input = input("📊 How many jobs to scrape? (default: 25, max: 100): ").strip()
        if not max_jobs_input:
            max_jobs = 25
            break
        try:
            max_jobs = int(max_jobs_input)
            if max_jobs <= 0:
                print("❌ Number of jobs must be positive!")
            elif max_jobs > 100:
                print("⚠️ Scraping more than 100 jobs may be slow and could trigger rate limiting.")
                confirm = input("Proceed? (y/n): ").strip().lower()
                if confirm in ["y", "yes"]:
                    break
            else:
                break
        except ValueError:
            print("❌ Please enter a valid number!")

    print("\n📁 Filename options:")
    print("1. Auto-generate filename (recommended)")
    print("2. Enter custom filename")
    while True:
        choice = input("Enter your choice (1 or 2): ").strip()
        if choice in ["1", "2"]:
            break
        print("❌ Please enter 1 or 2!")
    if choice == "2":
        filename = input("💾 Enter filename (without .csv): ").strip()
        while not filename:
            print("❌ Filename cannot be empty!")
            filename = input("💾 Enter filename: ").strip()
        if not filename.endswith('.csv'):
            filename += '.csv'
    else:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{job_title.replace(' ', '_')}_{job_location.replace(' ', '_')}_{max_jobs}jobs_{timestamp}.csv"
    return job_title, job_location, max_jobs, filename, date_filter, exp_filter


def fetch_job_ids(title: str, location: str, max_jobs: int, date_filter: str = "", exp_filter: str = "") -> List[str]:
    """
    Fetch job IDs from LinkedIn search results, supporting pagination and filters.
    """
    ids = []
    start = 0
    page_size = 25
    while len(ids) < max_jobs:
        # Build URL with proper encoding for special characters
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
                print(f"❌ Failed to fetch job listings. Status code: {resp.status_code}")
                break
            soup = BeautifulSoup(resp.text, "html.parser")
            jobs = soup.find_all("li")
            if not jobs:
                print("⚠️ No more jobs found on this page. Stopping pagination.")
                break
            for job in jobs:
                base_card = job.find("div", {"class": "base-card"})
                if base_card and base_card.get("data-entity-urn"):
                    try:
                        job_id = base_card.get("data-entity-urn").split(":")[3]
                        if job_id not in ids:
                            ids.append(job_id)
                        if len(ids) >= max_jobs:
                            break
                    except Exception as e:
                        print(f"⚠️ Error parsing job ID: {e}")
            start += page_size
            time.sleep(random.uniform(1, 2))
        except requests.RequestException as e:
            print(f"❌ Network error: {e}")
            break
    return ids


def fetch_job_details(job_id: str) -> Optional[Dict[str, Optional[str]]]:
    """
    Fetch and parse job details for a given job ID.
    """
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
    try:
        resp = requests.get(url)
        if resp.status_code != 200:
            print(f"   ❌ Failed to fetch job {job_id}")
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        job = {
            "job_url": f"https://www.linkedin.com/jobs/view/{job_id}",
            "job_title": None,
            "company_name": None,
            "job_location": None,
            "time_posted": None,
            "num_applicants": None,
            "job_description_preview": None
        }
        title_el = soup.find("h2", {"class": "top-card-layout__title font-sans text-lg papabear:text-xl font-bold leading-open text-color-text mb-0 topcard__title"})
        if title_el:
            job["job_title"] = title_el.text.strip()
        company_el = soup.find("a", {"class": "topcard__org-name-link topcard__flavor--black-link"})
        if company_el:
            job["company_name"] = company_el.text.strip()
        location_el = soup.find("span", {"class": "topcard__flavor--bullet"})
        if location_el:
            job["job_location"] = location_el.text.strip()
        time_el = soup.find("span", {"class": "posted-time-ago__text topcard__flavor--metadata"})
        if time_el:
            job["time_posted"] = time_el.text.strip()
        applicants_el = soup.find("span", {"class": "num-applicants__caption topcard__flavor--metadata topcard__flavor--bullet"})
        if applicants_el:
            job["num_applicants"] = applicants_el.text.strip()
        desc_el = soup.find("div", {"class": "show-more-less-html__markup"})
        if desc_el:
            desc = desc_el.text.strip()
            job["job_description_preview"] = desc[:200] + ("..." if len(desc) > 200 else "")
        return job
    except Exception as e:
        print(f"   ❌ Error processing job {job_id}: {e}")
        return None


def scrape_linkedin_jobs(title: str, location: str, max_jobs: int, date_filter: str = "", exp_filter: str = "") -> pd.DataFrame:
    """
    Scrape LinkedIn jobs for a given title and location, with pagination and filters.
    Returns a DataFrame of job details.
    """
    print(f"🔍 Searching for '{title}' jobs in '{location}' (max {max_jobs})...")
    job_ids = fetch_job_ids(title, location, max_jobs, date_filter, exp_filter)
    if not job_ids:
        print("❌ No job IDs found.")
        return pd.DataFrame()
    print(f"📊 Found {len(job_ids)} job IDs.")
    jobs = []
    for i, job_id in enumerate(job_ids, 1):
        print(f"🔄 [{i}/{len(job_ids)}] Fetching job {job_id}")
        job = fetch_job_details(job_id)
        if job:
            jobs.append(job)
            print(f"   ✅ {job.get('job_title', 'Unknown Title')}")
        else:
            print(f"   ❌ Skipped job {job_id}")
        delay = random.uniform(1, 2.5)
        print(f"   ⏱️ Waiting {delay:.1f} seconds...")
        time.sleep(delay)
    df = pd.DataFrame(jobs)
    print(f"\n🎉 Scraping completed. Total jobs: {len(df)}")
    return df


def display_and_save_results(df: pd.DataFrame, filename: str) -> bool:
    """
    Display a summary of results and save to CSV.
    Returns True if save was successful.
    """
    if df.empty:
        print("❌ No jobs found. Check your search criteria or network.")
        return False
    print("\n🎯 Sample job listings:")
    print("=" * 80)
    for i, job in df.head(5).iterrows():
        print(f"\n{i+1}. 📋 {job['job_title'] or 'Unknown Title'}")
        print(f"   🏢 Company: {job['company_name'] or 'Unknown Company'}")
        print(f"   📍 Location: {job['job_location'] or 'Unknown Location'}")
        print(f"   📅 Posted: {job['time_posted'] or 'Unknown'}")
        print(f"   👥 Applicants: {job['num_applicants'] or 'Unknown'}")
        print(f"   🔗 **APPLY HERE:** {job['job_url']}")
        if job['job_description_preview']:
            print(f"   📝 Description: {job['job_description_preview']}")
        print("-" * 80)
    if len(df) > 5:
        print(f"\n📊 ... and {len(df) - 5} more jobs (see CSV for full list)")
    try:
        col_order = [
            'job_title', 'company_name', 'job_location',
            'time_posted', 'num_applicants', 'job_url',
            'job_description_preview'
        ]
        existing_cols = [c for c in col_order if c in df.columns]
        df = df.reindex(columns=existing_cols)
        df.to_csv(filename, index=False)
        print(f"\n💾 Results saved to {filename}")
        return True
    except Exception as e:
        print(f"❌ Error saving file: {e}")
        return False


def main():
    try:
        print("🚀 Starting LinkedIn Job Scraper...")
        job_title, job_location, max_jobs, filename, date_filter, exp_filter = get_user_input()
        print(f"\n📋 Search Summary:")
        print(f"   🔍 Job Title: {job_title}")
        print(f"   📍 Location: {job_location}")
        print(f"   📊 Max Jobs: {max_jobs}")
        print(f"   💾 Output File: {filename}")
        print(f"   🗓️ Date Posted Filter: {date_filter or 'Any time'}")
        print(f"   🎓 Experience Level Filter: {exp_filter or 'Any level'}")
        
        # Show date filter in human-readable format
        if date_filter == "r604800":
            print(f"   ⏰ **Searching for jobs posted in the last 7 days**")
        elif date_filter == "r2592000":
            print(f"   ⏰ **Searching for jobs posted in the last 30 days**")
        elif date_filter == "r86400":
            print(f"   ⏰ **Searching for jobs posted in the last 24 hours**")
        else:
            print(f"   ⏰ **Searching for jobs from any time**")
        
        # Show experience level filter in human-readable format
        exp_level_names = {
            "": "Any level",
            "1": "Internship",
            "2": "Entry level", 
            "3": "Associate",
            "4": "Mid-Senior level",
            "5": "Director",
            "6": "Executive"
        }
        
        if exp_filter:
            if "," in exp_filter:
                # Multiple levels selected
                selected_levels = exp_filter.split(",")
                level_names = [exp_level_names.get(level, f"Level {level}") for level in selected_levels]
                print(f"   🎓 **Experience Levels:** {', '.join(level_names)}")
            else:
                # Single level selected
                level_name = exp_level_names.get(exp_filter, f"Level {exp_filter}")
                print(f"   🎓 **Experience Level:** {level_name}")
        else:
            print(f"   🎓 **Experience Level:** Any level")
        
        print("-" * 60)
        proceed = input("\n🤔 Proceed with scraping? (y/n): ").strip().lower()
        if proceed not in ['y', 'yes']:
            print("❌ Scraping cancelled by user.")
            return
        print("\n🚀 Scraping in progress...")
        df = scrape_linkedin_jobs(job_title, job_location, max_jobs, date_filter, exp_filter)
        success = display_and_save_results(df, filename)
        if success:
            print(f"\n🎉 Job scraping completed successfully!")
            print(f"📁 Open '{filename}' to view your results.")
        else:
            print(f"\n⚠️ Scraping completed with issues. Please check the output above.")
    except KeyboardInterrupt:
        print("\n\n⚠️ Scraping interrupted by user (Ctrl+C). No data was saved.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("🔧 Please check your internet connection and try again.")
        print("💡 If the problem persists, LinkedIn may have changed their website structure.")


if __name__ == "__main__":
    print("=" * 60)
    print("🔍 LinkedIn Job Scraper - Starting Application")
    print("=" * 60)
    main()
    print("\n👋 Thank you for using LinkedIn Job Scraper!")
    print("⚖️ Please use this tool responsibly and respect LinkedIn's Terms of Service.")
