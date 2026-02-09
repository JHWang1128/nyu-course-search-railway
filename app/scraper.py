import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from .models import Course
# from .database import get_db

CATALOG_URL = "https://bulletins.nyu.edu/courses/"

# For fetch_details, we need to inspect the network requests.
# Based on common Leepfrog implementations (which NYU uses), there's usually a POST to an API.
# I'll add a placeholder implementation for now.

import asyncio

async def scrape_catalog(db: Session):
    """
    Scrapes the main course catalog by first getting all subject pages,
    then scraping courses from each subject page.
    """
    try:
        print("Fetching subject list...")
        async with httpx.AsyncClient() as client:
            response = await client.get(CATALOG_URL)
            response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Find all subject links
        # Selector: .az_sitemap ul li a
        subject_links = []
        for a in soup.select(".az_sitemap ul li a"):
            href = a.get("href")
            if href and href.startswith("/courses/"):
                full_url = "https://bulletins.nyu.edu" + href
                subject_links.append(full_url)
        
        print(f"Found {len(subject_links)} subject pages. Starting scrape...")
        
        # Concurrency control
        sem = asyncio.Semaphore(5) # Limit to 5 concurrent requests
        total_courses_added = 0
        total_courses_found = 0
        
        async def scrape_subject(url):
            nonlocal total_courses_added, total_courses_found
            async with sem:
                try:
                    async with httpx.AsyncClient() as client:
                        resp = await client.get(url)
                        # Some pages might timeout or 404
                        if resp.status_code != 200:
                            print(f"Failed to fetch {url}: {resp.status_code}")
                            return
                        
                    subj_soup = BeautifulSoup(resp.text, "html.parser")
                    course_blocks = subj_soup.select(".courseblock")
                    
                    for block in course_blocks:
                        code_el = block.select_one(".detail-code")
                        title_el = block.select_one(".detail-title")
                        desc_el = block.select_one(".courseblockextra")
                        
                        if code_el and title_el:
                            code = code_el.get_text(separator=" ", strip=True)
                            title = title_el.get_text(separator=" ", strip=True)
                            desc = desc_el.get_text(separator=" ", strip=True) if desc_el else ""
                            
                            # Check existence (In production, load all codes in memory first to avoid N queries)
                            # For now, simplistic individual check
                            existing = db.query(Course).filter(Course.course_code == code).first()
                            if not existing:
                                new_course = Course(course_code=code, title=title, description=desc)
                                db.add(new_course)
                                total_courses_added += 1
                            total_courses_found += 1
                            
                except Exception as ex:
                    print(f"Error scraping {url}: {ex}")

        # Gather all tasks
        tasks = [scrape_subject(link) for link in subject_links]
        
        # Process in chunks with progress tracking if needed, but gather is fine for ~600 links with semaphore
        # To avoid overwhelming, let's just do all with the semaphore.
        await asyncio.gather(*tasks)
        
        db.commit()
        return {"status": "success", "added": total_courses_added, "total_found": total_courses_found, "subjects_scanned": len(subject_links)}
        
    except Exception as e:
        print(f"Scrape Error: {e}")
        return {"status": "error", "detail": str(e)}

async def fetch_details(course_code: str):
    # This requires more investigation into specific API endpoints
    return {"detail": "Not implemented"}
