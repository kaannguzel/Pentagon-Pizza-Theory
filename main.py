from playwright.sync_api import sync_playwright
import re
import os
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple

# -----------------------------
# CONFIG
# -----------------------------

HEADLESS = False
PROFILE_PATH = os.path.join(os.getcwd(), "pw_profile")

PLACE_URLS = [
    "https://www.google.com/maps/place/Domino's+Pizza/@38.8627308,-77.0879692,17z/data=!3m1!4b1!4m6!3m5!1s0x89b7b6ba2b02a023:0x15622e1516edc315!8m2!3d38.8627267!4d-77.0853943!16s%2Fg%2F1wbryp46?entry=ttu&g_ep=EgoyMDI1MDYxNi4wIKXMDSoASAFQAw%3D%3D",
    "https://www.google.com/maps/place/Extreme+Pizza/@38.8602396,-77.0585603,17z/data=!3m1!4b1!4m6!3m5!1s0x89b7b72778ab8871:0x3762c646ac6ddfe1!8m2!3d38.8602396!4d-77.0559854!16s%2Fg%2F12llsn19l?entry=ttu&g_ep=EgoyMDI1MDYxNi4wIKXMDSoASAFQAw%3D%3D",
    "https://www.google.com/maps/place/We,+The+Pizza/@38.8663614,-77.0588449,15.76z/data=!3m1!5s0x89b7b72f331803b7:0x7edf0a3adffa41c8!4m6!3m5!1s0x89b7b72f38e95a4b:0xc933eda7e98cbcb0!8m2!3d38.8551791!4d-77.049733!16s%2Fg%2F1q62g66vf?entry=ttu&g_ep=EgoyMDI1MDYxNi4wIKXMDSoASAFQAw%3D%3D",
    "https://www.google.com/maps/place/Pizzato+Pizza/@38.8791607,-77.096414,15.18z/data=!4m6!3m5!1s0x89b7b709fda7b8ad:0x583383fdc3ad2c55!8m2!3d38.8806865!4d-77.089827!16s%2Fg%2F11v5zglw6h?entry=ttu&g_ep=EgoyMDI1MDYxNy4wIKXMDSoASAFQAw%3D%3D",
    "https://www.google.com/maps/place/Papa+Johns+Pizza/@38.8292633,-77.1901741,11z/data=!4m6!3m5!1s0x89b7b77f69c14da3:0xa3bad34a334f286f!8m2!3d38.8606821!4d-77.0922272!16s%2Fg%2F11t104lmtl?entry=ttu&g_ep=EgoyMDI1MTIwOS4wIKXMDSoASAFQAw%3D%3D"
]

# -----------------------------
# DATA MODELS
# -----------------------------

@dataclass
class LivePopularity:
    current_pct: Optional[int]
    usual_pct: Optional[int]
    raw_text: Optional[str]
    current_time_label: Optional[str] = None  # e.g. "12 PM"

# -----------------------------
# UTILS
# -----------------------------

def round_to_nearest_10(n: float) -> int:
    # 263 -> 260, 267 -> 270 (looks more “rounded”)
    return int(round(n / 10.0) * 10)

def normalize_time_label(s: str) -> Optional[str]:
    # Tries to normalize things like "12 PM", "12PM", "12 p.m."
    s = s.strip().lower()
    s = s.replace(".", "").replace(" ", "")
    m = re.match(r"^(\d{1,2})(am|pm)$", s)
    if not m:
        return None
    hour = int(m.group(1))
    ap = m.group(2).upper()
    return f"{hour} {ap}"

# -----------------------------
# PIZZINT-STYLE KEYWORD MAPPING
# -----------------------------

def pizzint_style_keyword(current: int, usual: Optional[int]) -> Dict[str, Any]:
    if usual is None or usual == 0:
        return {"label": "unknown", "delta": None, "spike_ratio_pct": None}

    diff = current - usual

    if diff <= -35:
        label = "much quieter than usual"
    elif diff <= -15:
        label = "quieter than usual"
    elif diff <= -5:
        label = "quiet"
    elif diff <= 5:
        label = "normal"
    elif diff <= 15:
        label = "a little busy"
    elif diff <= 30:
        label = "busier than usual"
    else:
        label = "much busier than usual"

    # Pizzint-like: current/usual * 100 (not an increase, a ratio)
    spike_ratio = None
    if current > usual:
        spike_ratio = round_to_nearest_10((current / usual) * 100.0)

    return {"label": label, "delta": diff, "spike_ratio_pct": spike_ratio}

# -----------------------------
# SCRAPING HELPERS
# -----------------------------

def accept_google_consent_if_any(page) -> None:
    candidates = [
        'button:has-text("Accept all")',
        'button:has-text("I agree")',
        'button:has-text("Accept")',
        'button:has-text("Agree")',
        'button:has-text("Kabul ediyorum")',
        'button:has-text("Tümünü kabul et")',
        'button:has-text("Kabul et")',
    ]
    for sel in candidates:
        try:
            page.click(sel, timeout=2000)
            page.wait_for_timeout(800)
            break
        except:
            pass

def extract_place_name(page) -> str:
    try:
        name = page.locator('h1[class*="DUwDvf"]')
        name.wait_for(timeout=20000)
        return name.inner_text().strip()
    except:
        return "Unknown Place"

def ensure_popular_times_visible(page) -> None:
    """
    Popular times alanı bazen aşağıda kalıyor.
    Bu fonksiyon scroll ederek 'Popular times' / 'Popüler saatler' benzeri metni arar.
    """
    # The main Google Maps content panel is usually inside this scroller
    # (it can change, but at least pushing the page down tends to work)
    for _ in range(12):
        try:
            # English/Turkish variants
            if page.get_by_text("Popular times").first.is_visible(timeout=800):
                return
        except:
            pass
        try:
            if page.get_by_text("Popüler saatler").first.is_visible(timeout=800):
                return
        except:
            pass

        # Try scrolling (page or left panel)
        try:
            page.mouse.wheel(0, 900)
        except:
            pass
        page.wait_for_timeout(600)

def extract_live_from_bars(page) -> LivePopularity:
    """
    Öncelik: histogram bar aria-label'larından current/usual çekmek.
    Hedef:
      - "Currently X% busy" geçen bar => current
      - Aynı saat için "Usually Y% busy" geçen bar => usual
    """
    # Collect elements whose aria-label relates to popular times
    # (Google changes the DOM often; we scan broadly but will filter)
    try:
        loc = page.locator('[aria-label*="busy"], [aria-label*="Busy"], [aria-label*="meşgul"], [aria-label*="Meşgul"]')
        count = loc.count()
        if count == 0:
            return LivePopularity(None, None, None, None)

        labels: List[str] = []
        # Reasonable limit to keep it from growing too large
        for i in range(min(count, 500)):
            try:
                a = loc.nth(i).get_attribute("aria-label")
                if a:
                    labels.append(a)
            except:
                continue
    except:
        return LivePopularity(None, None, None, None)

    # Normalize + filter
    norm = [x.strip() for x in labels if "%" in x and ("busy" in x.lower() or "meşgul" in x.lower())]

    # 1) Find the current bar
    current_pct = None
    current_time = None
    current_raw = None

    for t in norm:
        low = t.lower()
        if "currently" in low or "şu anda" in low:
            m_pct = re.search(r"(\d+)%", low)
            # Capture the time at the beginning if present (e.g. "12 PM: Currently 40% busy.")
            m_time = re.match(r"^\s*([0-9]{1,2}\s*(?:am|pm|a\.m\.|p\.m\.))", low)
            if m_pct:
                current_pct = int(m_pct.group(1))
                current_raw = t
                if m_time:
                    current_time = normalize_time_label(m_time.group(1))
                break

    # 2) Find the usual bar (for the same hour)
    usual_pct = None
    if current_time:
        # The "usually" line containing the same time label
        for t in norm:
            low = t.lower()
            if "usually" in low or "genelde" in low or "normalde" in low:
                # Same hour?
                if current_time.lower().replace(" ", "") in low.replace(" ", "").replace(".", ""):
                    m_pct = re.search(r"(\d+)%", low)
                    if m_pct:
                        usual_pct = int(m_pct.group(1))
                        break

    # 3) If there is no time match, fallback: look for a single line like "currently X% ... usually Y%"
    if current_pct is None or usual_pct is None:
        for t in norm:
            low = t.lower()
            if "currently" in low and "usually" in low:
                m1 = re.search(r"currently\s+(\d+)%", low)
                m2 = re.search(r"usually\s+(\d+)%", low)
                if m1 and current_pct is None:
                    current_pct = int(m1.group(1))
                    current_raw = t
                if m2 and usual_pct is None:
                    usual_pct = int(m2.group(1))
                    if current_raw is None:
                        current_raw = t
                if current_pct is not None and usual_pct is not None:
                    break

    # If we couldn't find current (some places have no live), there may still be a usual bar, but Pizzint needs current
    return LivePopularity(current_pct, usual_pct, current_raw, current_time)

def extract_live_percentages_fallback(page) -> LivePopularity:
    """
    Eski yöntem (genel aria-label tarama) – bar yöntemi başarısız olursa fallback.
    """
    try:
        elements = page.locator("[aria-label]")
        count = elements.count()
    except:
        return LivePopularity(None, None, None, None)

    for i in range(min(count, 800)):
        try:
            label = elements.nth(i).get_attribute("aria-label")
            if not label:
                continue
            text = label.lower()
            if "currently" in text and "%" in text:
                current_match = re.search(r"currently\s+(\d+)%", text)
                usual_match = re.search(r"usually\s+(\d+)%", text)
                current = int(current_match.group(1)) if current_match else None
                usual = int(usual_match.group(1)) if usual_match else None
                return LivePopularity(current, usual, text, None)
        except:
            continue

    return LivePopularity(None, None, None, None)

# -----------------------------
# MAIN SCRAPER
# -----------------------------

def scrape_place(page, url: str) -> Dict[str, Any]:
    page.goto(url, timeout=60000, wait_until="domcontentloaded")
    page.wait_for_load_state("domcontentloaded", timeout=45000)

# For Google Maps: waiting until the place name (h1) appears is much more stable
    try:
        page.locator('h1[class*="DUwDvf"]').wait_for(timeout=45000)
    except:
        pass

    accept_google_consent_if_any(page)

    # On some pages, after closing the consent dialog, the content reloads
    try:
        page.wait_for_load_state("networkidle", timeout=20000)
    except:
        pass

    # Make the Popular times section visible
    ensure_popular_times_visible(page)

    place_name = extract_place_name(page)

    # Try the bars first
    live = extract_live_from_bars(page)

    # If that doesn’t work, use the fallback
    if live.current_pct is None:
        live2 = extract_live_percentages_fallback(page)
        # Take current from the fallback; if usual exists, use that too
        live = LivePopularity(
            current_pct=live2.current_pct,
            usual_pct=live.usual_pct if live.usual_pct is not None else live2.usual_pct,
            raw_text=live2.raw_text,
            current_time_label=live.current_time_label
        )

    result: Dict[str, Any] = {
        "place_name": place_name,
        "current_pct": live.current_pct,
        "usual_pct": live.usual_pct,
        "raw_live_text": live.raw_text,
        "keyword": None,
        "delta": None,
        "spike": None,
        "time": live.current_time_label,
    }

    if live.current_pct is not None and live.usual_pct is not None:
        mapping = pizzint_style_keyword(live.current_pct, live.usual_pct)
        result["keyword"] = mapping["label"]
        result["delta"] = mapping["delta"]

        # Like Pizzint: show a spike if ratio >= 200% (e.g. 270%)
        if mapping["spike_ratio_pct"] is not None and mapping["spike_ratio_pct"] >= 200:
            result["spike"] = f'{mapping["spike_ratio_pct"]}% spike'

    return result

# -----------------------------
# RUN
# -----------------------------

if __name__ == "__main__":
    print("\n--- LIVE POPULARITY (BAR-BASED) ---\n")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_PATH,
            headless=HEADLESS,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
            ],
        )
        page = context.new_page()

        for url in PLACE_URLS:
            print(f"Scraping: {url}")
            r = scrape_place(page, url)

            print(f"Place:   {r['place_name']}")
            print(f"Time:    {r['time']}")
            print(f"Current: {r['current_pct']}%")
            print(f"Usual:   {r['usual_pct']}%")
            print(f"Delta:   {r['delta']}")
            print(f"Keyword: {r['keyword']}")
            if r["spike"]:
                print(f"Spike:   {r['spike']}")
            print(f"RAW:     {r['raw_live_text']}")
            print("-" * 70)

        context.close()
