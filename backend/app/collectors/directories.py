import asyncio
import re
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup

from app.collectors.base import BaseCollector
from app.config import SCRAPING_CONFIG


class ApontadorCollector(BaseCollector):
    def __init__(self):
        super().__init__()
        self.name = "apontador"

    async def collect(self, niche: str, city: str, max_results: int = 30, country: str = "") -> list[dict]:
        results = []
        query = f"{niche} {city}"
        search_url = f"https://www.apontador.com.br/busca/{quote(query)}"

        headers = {"User-Agent": SCRAPING_CONFIG["user_agent"]}
        async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers=headers) as client:
            try:
                resp = await client.get(search_url)
                if resp.status_code != 200:
                    self.errors.append(f"Apontador returned {resp.status_code}")
                    # Return empty, not critical
                    return results

                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.select('[data-testid="business-card"], .business-card, .card-result')

                for card in cards[:max_results]:
                    try:
                        name_el = card.select_one("h2, .business-name, .card-title")
                        name = name_el.get_text(strip=True) if name_el else ""

                        phone_el = card.select_one('[href^="tel:"], .phone, .telefone')
                        phone = ""
                        if phone_el:
                            href = phone_el.get("href", "")
                            phone = href.replace("tel:", "") if href else phone_el.get_text(strip=True)

                        site_el = card.select_one('[href^="http"], .site, .website')
                        site = site_el.get("href", "") if site_el else ""

                        addr_el = card.select_one(".address, .endereco, .street-address")
                        address = addr_el.get_text(strip=True) if addr_el else ""

                        if name:
                            whatsapp = ""
                            if phone:
                                digits = re.sub(r'\D', '', phone)
                                whatsapp = f"https://wa.me/55{digits}" if digits.startswith("55") else f"https://wa.me/{digits}"

                            results.append(self.build_result(
                                company_name=name,
                                phone=phone,
                                whatsapp_link=whatsapp,
                                website=site,
                                address=address,
                                source_url=search_url,
                            ))
                    except Exception:
                        continue

            except Exception as e:
                self.errors.append(f"Apontador error: {e}")

        self.results = results
        return results


class ListaBrasilCollector(BaseCollector):
    def __init__(self):
        super().__init__()
        self.name = "lista_brasil"

    async def collect(self, niche: str, city: str, max_results: int = 30, country: str = "") -> list[dict]:
        results = []
        query = f"{niche} {city}"
        search_url = f"https://www.listabrasil.com.br/busca?q={quote(query)}"

        headers = {"User-Agent": SCRAPING_CONFIG["user_agent"]}
        async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers=headers) as client:
            try:
                resp = await client.get(search_url)
                if resp.status_code != 200:
                    return results

                soup = BeautifulSoup(resp.text, "html.parser")

                for item in soup.select(".result-item, .listing-item, .card")[:max_results]:
                    try:
                        name_el = item.select_one("h3, h2, .title")
                        name = name_el.get_text(strip=True) if name_el else ""

                        phone_el = item.select_one('[href^="tel:"], .phone')
                        phone = phone_el.get("href", "").replace("tel:", "") if phone_el else ""

                        site_el = item.select_one('[href^="http"], .site')
                        site = site_el.get("href", "") if site_el else ""

                        addr_el = item.select_one(".address, .endereco")
                        address = addr_el.get_text(strip=True) if addr_el else ""

                        if name:
                            whatsapp = ""
                            if phone:
                                digits = re.sub(r'\D', '', phone)
                                whatsapp = f"https://wa.me/55{digits}" if digits.startswith("55") else f"https://wa.me/{digits}"

                            results.append(self.build_result(
                                company_name=name,
                                phone=phone,
                                whatsapp_link=whatsapp,
                                website=site,
                                address=address,
                                source_url=search_url,
                            ))
                    except Exception:
                        continue

            except Exception as e:
                self.errors.append(f"ListaBrasil error: {e}")

        self.results = results
        return results

