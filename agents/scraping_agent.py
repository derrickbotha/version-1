"""
Scraping Agent — uses Playwright to scrape LMS course pages and
build a DOM knowledge graph so selectors are cached and reused.
"""
import logging
import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

def scrape_course(lms_url: str, username: str, password: str,
                  course_url: str) -> Dict[str, Any]:
    """
    Login to LMS and scrape all assignments, deadlines, and resources.
    Caches DOM selectors in dom_graphs directory.
    """
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page    = browser.new_page(viewport={"width": 1280, "height": 900})
            page.set_default_timeout(30000)

            # Detect LMS type
            lms_type = _detect_lms_type(lms_url)
            selectors = _get_selectors(lms_type)

            # Login
            page.goto(f"{lms_url.rstrip('/')}/login/index.php")
            page.fill(selectors["username"], username)
            page.fill(selectors["password"], password)
            page.click(selectors["login_btn"])
            page.wait_for_timeout(3000)

            if "login" in page.url.lower():
                raise Exception("Login failed")

            # Load course
            page.goto(course_url)
            page.wait_for_load_state("domcontentloaded")

            # Scrape assignments
            assignments = _scrape_assignments(page)
            weeks       = _scrape_weeks(page)
            resources   = _scrape_resources(page)

            # Visit each assignment for details
            assignment_details = []
            for a in assignments:
                if "/mod/assign" in a["href"]:
                    page.goto(a["href"])
                    page.wait_for_load_state("domcontentloaded")
                    detail = page.evaluate("""() => ({
                        fullText:    document.body.innerText,
                        description: document.querySelector('.assignmentintro, .activity-description')?.innerText?.trim() || '',
                        dateText:    document.querySelector('.submissionstatustable, table.generaltable')?.innerText || '',
                    })""")
                    assignment_details.append({**a, **detail})

            browser.close()

            # Cache DOM selectors
            _cache_dom_selectors(lms_url, lms_type, selectors)

            return {
                "lms_type": lms_type,
                "weeks": weeks,
                "assignments": assignments,
                "assignment_details": assignment_details,
                "resources": resources,
                "scraped_at": datetime.utcnow().isoformat(),
            }

    except Exception as e:
        logger.error(f"Scraping error: {e}")
        return {"error": str(e), "scraped_at": datetime.utcnow().isoformat()}

def _detect_lms_type(url: str) -> str:
    """Detect which LMS is being used from the URL."""
    url_lower = url.lower()
    if "moodle" in url_lower or "vle" in url_lower or "unicaf" in url_lower:
        return "moodle"
    elif "canvas" in url_lower:
        return "canvas"
    elif "blackboard" in url_lower:
        return "blackboard"
    elif "brightspace" in url_lower or "d2l" in url_lower:
        return "brightspace"
    return "moodle"  # default

def _get_selectors(lms_type: str) -> Dict[str, str]:
    """Return CSS selectors for each LMS type."""
    selectors = {
        "moodle": {
            "username":         "#username",
            "password":         "#password",
            "login_btn":        "#loginbtn",
            "week_section":     "li.section, .section.main, .course-section",
            "week_heading":     "h3, .sectionname, .section-title",
            "assignment_link":  "a[href*='/mod/assign']",
            "upload_btn":       ".fp-btn-add button",
            "file_input":       "input[name='repo_upload_file']",
            "save_btn":         "input[name='submitbutton'], #id_submitbutton",
            "submit_btn":       "input[value='Submit assignment']",
            "intro":            ".assignmentintro, .activity-description",
        },
        "canvas": {
            "username":         "#pseudonym_session_unique_id",
            "password":         "#pseudonym_session_password",
            "login_btn":        ".Button--login",
            "week_section":     ".ig-list .ig-row",
            "week_heading":     ".ig-title",
            "assignment_link":  "a[href*='/assignments/']",
            "upload_btn":       ".FileDrop",
            "file_input":       "input[type='file']",
            "save_btn":         ".btn-primary",
            "submit_btn":       ".submit_assignment_link",
            "intro":            ".description",
        },
        "blackboard": {
            "username":         "#user_id",
            "password":         "#password",
            "login_btn":        "#entry-login",
            "week_section":     ".courseMenu li",
            "week_heading":     ".courseMenu a",
            "assignment_link":  "a[href*='assessment']",
            "upload_btn":       ".attachFileButton",
            "file_input":       "input[type='file']",
            "save_btn":         "#bottom_Submit",
            "submit_btn":       "#bottom_Submit",
            "intro":            "#instructions",
        },
    }
    return selectors.get(lms_type, selectors["moodle"])

def _scrape_assignments(page) -> List[Dict]:
    return page.evaluate("""() => {
        const links = [];
        document.querySelectorAll('a[href*="/mod/assign"]').forEach(a => {
            links.push({text: a.innerText.trim(), href: a.href});
        });
        return links;
    }""")

def _scrape_weeks(page) -> List[Dict]:
    return page.evaluate("""() => {
        const out = [];
        const secs = document.querySelectorAll('li.section, .section.main, .course-section');
        secs.forEach(sec => {
            const head = sec.querySelector('h3, .sectionname, .section-title');
            const links = [];
            sec.querySelectorAll('a[href]').forEach(a => links.push({text: a.innerText.trim(), href: a.href}));
            out.push({heading: head ? head.innerText.trim() : '', text: sec.innerText.trim().slice(0, 500), links});
        });
        return out;
    }""")

def _scrape_resources(page) -> List[Dict]:
    return page.evaluate("""() => {
        const links = [];
        document.querySelectorAll('a[href*="/mod/resource"], a[href*="/mod/folder"], a[href*="/mod/page"]').forEach(a => {
            links.push({text: a.innerText.trim(), href: a.href});
        });
        return links;
    }""")

def _cache_dom_selectors(lms_url: str, lms_type: str, selectors: Dict):
    """Save DOM selectors to disk cache for reuse."""
    cache_dir = os.path.join(os.path.dirname(__file__), "..", "knowledge_graph", "dom_cache")
    os.makedirs(cache_dir, exist_ok=True)
    safe_url = lms_url.replace("://", "_").replace("/", "_")[:50]
    cache_file = os.path.join(cache_dir, f"{safe_url}.json")
    with open(cache_file, "w") as f:
        json.dump({"lms_type": lms_type, "selectors": selectors, "cached_at": datetime.utcnow().isoformat()}, f, indent=2)
    logger.info(f"DOM selectors cached: {cache_file}")

def get_cached_selectors(lms_url: str) -> Optional[Dict]:
    """Load cached DOM selectors if available."""
    cache_dir = os.path.join(os.path.dirname(__file__), "..", "knowledge_graph", "dom_cache")
    safe_url  = lms_url.replace("://", "_").replace("/", "_")[:50]
    cache_file = os.path.join(cache_dir, f"{safe_url}.json")
    if os.path.exists(cache_file):
        with open(cache_file) as f:
            return json.load(f)
    return None
