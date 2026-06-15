import asyncio
import re
from typing import Optional
from urllib.parse import quote

from app.collectors.base import BaseCollector
from app.config import SCRAPING_CONFIG


class GoogleMapsCollector(BaseCollector):
    def __init__(self):
        super().__init__()
        self.name = "google_maps"

    async def collect(self, niche: str, city: str, max_results: int = 30, country: str = "Brasil") -> list[dict]:
        query = f"{niche} {city} {country}" if country.lower() != "brasil" else f"{niche} {city}"
        results = []

        try:
            results = await self._collect_playwright(query, max_results, country)
        except Exception as e:
            self.errors.append(f"Google Maps error: {e}")

        for r in results:
            r["source"] = self.name
        self.results = results
        return results

    async def _collect_playwright(self, query: str, max_results: int, country: str = "Brasil") -> list[dict]:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise ImportError("Playwright not installed")

        results = []
        locale_map = {
            "brasil": "pt-BR", "portugal": "pt-PT", "eua": "en-US",
            "estados unidos": "en-US", "reino unido": "en-GB",
            "inglaterra": "en-GB", "espanha": "es-ES", "frança": "fr-FR",
            "alemanha": "de-DE", "itália": "it-IT", "italia": "it-IT",
            "argentina": "es-AR", "méxico": "es-MX", "mexico": "es-MX",
            "canadá": "en-CA", "canada": "en-CA", "austrália": "en-AU",
            "australia": "en-AU", "japão": "ja-JP", "japao": "ja-JP",
        }
        locale = locale_map.get(country.lower().strip(), "en-US")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=SCRAPING_CONFIG["user_agent"],
                viewport={"width": 1920, "height": 1080},
                locale=locale,
            )
            page = await context.new_page()

            search_url = f"https://www.google.com/maps/search/{quote(query)}/"
            await page.goto(search_url, timeout=30000)
            await page.wait_for_timeout(4000)

            # Scroll to load all results (up to max_results * 2 to ensure we have enough)
            max_scrolls = max(20, max_results // 2)
            for i in range(max_scrolls):
                await page.evaluate("""
                    const feed = document.querySelector('[role="feed"]');
                    if (feed) feed.scrollBy(0, feed.clientHeight);
                """)
                await page.wait_for_timeout(1500)
                card_count = await page.evaluate(
                    "document.querySelectorAll('[role=\"article\"], a[href*=\"maps/place\"]').length"
                )
                if card_count >= max_results * 2:
                    break

            # Try multiple selectors to capture all cards
            cards = await page.query_selector_all(
                'div[role="article"], a[href*="maps/place"], div[jsaction*="pane.place"]'
            )
            self.errors.append(f"Found {len(cards)} cards from Google Maps (scrolled {i+1}x)")

            seen_names = set()
            for card in cards[:max_results * 2]:
                data = await self._extract_card_data(page, card, search_url)
                if data and data.get("company_name"):
                    name = data["company_name"].lower().strip()
                    if name not in seen_names:
                        seen_names.add(name)
                        results.append(data)
                    if len(results) >= max_results:
                        break

            # Fallback: extract from all visible place links if we got too few
            if len(results) < 5:
                self.errors.append("Few results, trying fallback extraction...")
                fallback_results = await self._extract_fallback(page, query, max_results)
                for r in fallback_results:
                    name = r.get("company_name", "").lower().strip()
                    if name and name not in seen_names:
                        seen_names.add(name)
                        results.append(r)

            await browser.close()

        return results[:max_results]

    async def _extract_card_data(self, page, card, search_url: str = "") -> Optional[dict]:
        try:
            text = await card.inner_text()
        except Exception:
            return None

        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if not lines:
            return None

        name = lines[0] if len(lines) > 0 else ""
        if not name or len(name) < 3:
            return None

        phone = ""
        website = ""
        address = ""
        category = ""
        rating = ""

        for line in lines:
            phone_match = re.search(r'(\(\d{2,}\)\s*\d{4,5}-?\d{4})', line)
            if phone_match and not phone:
                phone = re.sub(r'\D', '', phone_match.group(1))

            if "website" in line.lower():
                try:
                    links = await card.query_selector_all("a")
                    for link in links:
                        href = await link.get_attribute("href")
                        if href and "google.com/maps" not in href.lower() and href.startswith("http"):
                            website = href
                            break
                except Exception:
                    pass

            if "·" in line:
                parts = [p.strip() for p in line.split("·")]
                if len(parts) >= 2 and not category and len(parts[0]) < 80:
                    category = parts[0]
                    for p in parts[1:]:
                        if re.search(r'[A-Z]{2}\s*\d{5}', p) or "Rua" in p or "Avenida" in p or r"Av." in p or "-" in p:
                            if not address:
                                address = p.strip()

            if re.match(r'^[\d,.]+$', line.replace(",", ".")):
                rating = line

        # Also try to extract from href
        if not website:
            try:
                link_el = await card.query_selector("a.hfpxzc")
                if link_el:
                    href = await link_el.get_attribute("href")
                    website_btn = await card.query_selector('a[aria-label*="Site"], a[href*="http"]:not([href*="google"])')
                    if website_btn:
                        href_w = await website_btn.get_attribute("href")
                        if href_w and "google.com/maps" not in href_w.lower():
                            website = href_w
            except Exception:
                pass

        # Extract the specific place URL from the card
        maps_url = ""
        try:
            card_tag = await card.query_selector("a")
            if card_tag:
                href = await card_tag.get_attribute("href")
                if href and "maps/place" in href:
                    maps_url = href.split("?")[0] if "?" in href else href
            if not maps_url:
                main_link = await card.query_selector("a.hfpxzc")
                if main_link:
                    href = await main_link.get_attribute("href")
                    if href:
                        maps_url = href.split("?")[0] if "?" in href else href
        except Exception:
            pass

        address = self._clean_address(address)
        lead_city, state, neighborhood = self._parse_address(address)

        whatsapp = ""
        if phone:
            digits = re.sub(r'\D', '', phone)
            if len(digits) >= 10:
                whatsapp = f"https://wa.me/55{digits}" if not digits.startswith("55") else f"https://wa.me/{digits}"

        return self.build_result(
            company_name=name.strip(),
            category=category.strip(),
            phone=phone,
            whatsapp_link=whatsapp,
            website=website,
            address=address.strip(),
            neighborhood=neighborhood,
            lead_city=lead_city,
            state=state,
            source_url=maps_url or search_url,
        )

    def _clean_address(self, addr: str) -> str:
        if not addr:
            return ""
        addr = re.sub(r'\s+', ' ', addr).strip()
        return addr

    async def _extract_fallback(self, page, query: str, max_results: int) -> list[dict]:
        results = []
        try:
            links = await page.query_selector_all('a[href*="maps/place"]')
            seen = set()
            for link in links:
                href = await link.get_attribute("href")
                if not href:
                    continue
                text = await link.inner_text()
                text = text.strip()
                if not text or len(text) < 3:
                    continue
                name = text.split("\n")[0].strip()
                if name.lower() in seen:
                    continue
                seen.add(name.lower())
                maps_url = href.split("?")[0] if "?" in href else href
                results.append(self.build_result(
                    company_name=name,
                    source_url=maps_url,
                ))
                if len(results) >= max_results:
                    break
        except Exception as e:
            self.errors.append(f"Fallback extraction error: {e}")
        self.errors.append(f"Fallback extracted {len(results)} results")
        return results

    def _parse_address(self, address: str) -> tuple:
        city = ""
        state = ""
        neighborhood = ""
        if not address:
            return city, state, neighborhood
        parts = [p.strip() for p in address.split(",")]
        if len(parts) >= 2:
            neighborhood = parts[-3] if len(parts) >= 3 else ""
            city_state = parts[-2] if len(parts) >= 2 else address
            match = re.match(r'(.+?)\s*[-–]\s*([A-Z]{2})', city_state)
            if match:
                city = match.group(1).strip()
                state = match.group(2).strip()
            else:
                city = city_state
        return city, state, neighborhood
