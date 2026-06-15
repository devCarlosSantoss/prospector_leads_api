import asyncio
import re
from urllib.parse import quote, parse_qs, urlparse

import httpx
from bs4 import BeautifulSoup

from app.collectors.base import BaseCollector
from app.config import SCRAPING_CONFIG

DIRECTORY_DOMAINS = {
    "paginaamarela", "páginasamarelas", "yellowpages", "cylex",
    "guiatelefone", "telelistas", "listabrasil", "apontador",
    "eguias", "guiamais", "tudobem", "todosnegocios",
    "boaempresa", "empresasdobrasil", "solutudo", "encontraempresa",
    "guiafacil", "officiodirectory", "hotfrog", "mercadolivre",
    "facebook", "instagram", "twitter", "linkedin",
}


class DuckDuckGoCollector(BaseCollector):
    def __init__(self):
        super().__init__()
        self.name = "duckduckgo"
        self._target_state = ""

    async def collect(self, niche: str, city: str, max_results: int = 35, country: str = "") -> list[dict]:
        query = f"{niche} {city}"
        results = []
        seen_domains = set()

        negative = "-Espanha -Spain -Gasteiz -Wikipedia -wikidata -youtube"
        # Extract state abbreviation (e.g., "ES" from "Vitoria ES")
        state_parts = city.strip().split()
        state_abbr = state_parts[-1].upper() if len(state_parts) > 1 else ""
        self._target_state = state_abbr

        search_queries = [
            f"{query} site oficial {negative}",
            f"{query} empresa de {negative}",
            f"{niche} em {city} {negative}",
            f"{query} whatsapp telefone {negative}",
        ]

        async with httpx.AsyncClient(
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": SCRAPING_CONFIG["user_agent"]}
        ) as client:
            for sq in search_queries:
                try:
                    batch = await self._search_ddg(client, sq, max_results)
                    for item in batch:
                        domain = self._extract_domain(item.get("website", ""))
                        if domain and domain not in seen_domains and not self._is_directory(item, domain):
                            seen_domains.add(domain)
                            results.append(item)
                    await asyncio.sleep(1)
                except Exception as e:
                    self.errors.append(f"Busca '{sq[:30]}' erro: {e}")

        self.results = results
        return results

    def _is_directory(self, item: dict, domain: str) -> bool:
        domain_clean = re.sub(r'^(www\d?|m\.)\.', '', domain.split('.')[0] if domain else '')
        if domain_clean in DIRECTORY_DOMAINS:
            return True
        title = (item.get("company_name") or "").lower()
        list_signals = ["lista", "melhores", "encontre", "guia ", "diretório", "10 ", "top "]
        if any(s in title for s in list_signals):
            return True
        url_lower = (item.get("website") or "").lower()
        if any(d in url_lower for d in DIRECTORY_DOMAINS):
            return True
        return False

    async def _search_ddg(self, client: httpx.AsyncClient, query: str, max_r: int) -> list[dict]:
        results = []
        url = f"https://html.duckduckgo.com/html/?q={quote(query)}"

        try:
            resp = await client.get(url)
            if resp.status_code != 200:
                return results

            if "challenge-form" in resp.text or "anomaly.js" in resp.text:
                self.errors.append(f"DuckDuckGo captcha/block for query: '{query[:40]}'")
                return results

            soup = BeautifulSoup(resp.text, "html.parser")
            for result in soup.select(".result")[:max_r]:
                try:
                    title_el = result.select_one(".result__title a")
                    snippet_el = result.select_one(".result__snippet")

                    title = title_el.get_text(strip=True) if title_el else ""
                    link = str(title_el.get("href", "")) if title_el else ""
                    snippet = snippet_el.get_text(strip=True) if snippet_el else ""

                    if not title or not link or link == "#":
                        continue

                    if "uddg=" in link:
                        parsed = urlparse(link)
                        qs = parse_qs(parsed.query)
                        link = qs.get("uddg", [""])[0]

                    name = self._clean_business_name(title)
                    if not name:
                        continue

                    snippet_lower = (snippet or "").lower()
                    if self._is_directory_content(title, snippet_lower, link):
                        continue

                    if self._target_state and not self._mentions_state(snippet_lower, title.lower(), self._target_state):
                        if any(kw in (title + " " + snippet_lower).lower() for kw in
                               ["espanha", "spain", "gasteiz", "madrid", "barcelona"]):
                            continue

                    phone = self.extract_phone(snippet)
                    email = self.extract_email(snippet)
                    instagram = self.extract_instagram(snippet)

                    enriched = await self._enrich_from_page(client, link)
                    page_phone = enriched.get("phone", "")
                    page_email = enriched.get("email", "")
                    page_insta = enriched.get("instagram", "")

                    phone = phone or page_phone
                    email = email or page_email
                    instagram = instagram or page_insta

                    phone = self._validate_phone(phone)

                    whatsapp = ""
                    if phone:
                        digits = re.sub(r'\D', '', phone)
                        if digits:
                            whatsapp = f"https://wa.me/55{digits}" if digits.startswith("55") else f"https://wa.me/{digits}"

                    results.append(self.build_result(
                        company_name=name,
                        description=snippet[:300] if snippet else "",
                        website=link,
                        phone=phone or "",
                        whatsapp_link=whatsapp,
                        email=email or "",
                        instagram=instagram or "",
                        source_url=url,
                    ))
                except Exception:
                    continue

        except Exception as e:
            self.errors.append(f"DDG request error: {e}")

        return results

    def _is_directory_content(self, title: str, snippet_lower: str, url: str) -> bool:
        combined = (title + " " + snippet_lower).lower()
        signals = [
            r'\b(lista\s+de|10\s+melhores|os\s+melhores|melhores\s+clínicas|melhores\s+empresas)',
            r'(guia\s+de\s+|diretório\s+de|classificados\s+)',
            r'(página\s+\d+|resultados?\s+\d+|matches\s+\d+)',
            r'(telefone|endereço|como chegar|mapa do site)',
            r'(spain|españa|espanha|gasteiz|madrid|barcelona)',
        ]
        for sig in signals:
            if re.search(sig, combined):
                return True
        url_lower = url.lower()
        url_signals = ["paginaamarela", "guiamais", "eguias", "tudobem", "solutudo",
                       "hotfrog", "officiodirectory", "todosnegocios", "boaempresa",
                       "empresasdobrasil", "guiafacil", "encontraempresa"]
        if any(s in url_lower for s in url_signals):
            return True
        return False

    def _mentions_state(self, snippet_lower: str, title_lower: str, state_abbr: str) -> bool:
        if not state_abbr:
            return True
        state_names = {
            "AC": "acre", "AL": "alagoas", "AP": "amapá", "AM": "amazonas",
            "BA": "bahia", "CE": "ceará", "DF": "distrito federal",
            "ES": "espírito santo", "GO": "goiás", "MA": "maranhão",
            "MT": "mato grosso", "MS": "mato grosso do sul", "MG": "minas gerais",
            "PA": "pará", "PB": "paraíba", "PR": "paraná", "PE": "pernambuco",
            "PI": "piauí", "RJ": "rio de janeiro", "RN": "rio grande do norte",
            "RS": "rio grande do sul", "RO": "rondônia", "RR": "roraima",
            "SC": "santa catarina", "SP": "são paulo", "SE": "sergipe", "TO": "tocantins",
        }
        full_name = state_names.get(state_abbr, "").lower()
        state_abbr_lower = state_abbr.lower()
        combined = f"{title_lower} {snippet_lower}"

        exclude_words = ["espanha", "spain", "gasteiz", "madrid", "barcelona", "valencia"]
        if any(e in combined for e in exclude_words):
            return False

        if state_abbr_lower in combined or (full_name and full_name in combined):
            return True

        if state_abbr in {"ES", "SP", "RJ", "MG", "BA", "PR", "RS", "SC", "PE", "CE"}:
            return False
        return True

    def _clean_business_name(self, title: str) -> str:
        title = title.strip()
        if not title or len(title) < 3:
            return ""

        name = re.split(r'\s*[|–—-]\s*', title, maxsplit=1)[0].strip()
        name = re.sub(r'^[\d.]+[º°]\s*', '', name).strip()
        name = re.sub(r'\s*[☎📞📱💻🌐🖥️📧📍🔗⭐📌💈✂️💅👨‍⚕️👩‍⚕️👍✅✔️🎯🔥💯]\s*', ' ', name).strip()

        lower = name.lower().strip()
        generic_prefixes = {"início", "home", "contato", "fotos", "endereço", "telefone", "site",
                            "sobre", "blog", "produtos", "serviços", "galeria", "depoimentos",
                            "localização", "bem-vindo", "bem vindo", "welcome"}
        if lower in generic_prefixes or any(lower.startswith(g + " ") or lower.startswith(g + " -") for g in generic_prefixes):
            return ""

        noisy_patterns = [
            r'^(lista|10\s+|os\s+melhores|melhores\s+|encontre\s+|guia\s+|diretório\s+|classificados\s+|anúncio\s+|anúncios\s+)',
            r'^\d+\s*(?:resultados?|matches|melhores)',
            r'\s*[-–—|]\s*página\s+\d+$',
        ]
        for p in noisy_patterns:
            if re.search(p, lower):
                return ""

        name = name.strip(" -|,;:.\"'").strip()
        if len(name) < 3:
            return ""

        return name

    def _validate_phone(self, phone: str) -> str:
        if not phone:
            return ""
        digits = re.sub(r'\D', '', phone)
        if not digits:
            return ""

        if len(digits) >= 12 and digits.startswith("55"):
            digits = digits[2:]

        if not (10 <= len(digits) <= 11):
            return ""

        valid_ddds = [
            "11","12","13","14","15","16","17","18","19",
            "21","22","24","27","28",
            "31","32","33","34","35","37","38",
            "41","42","43","44","45","46","47","48","49",
            "51","53","54","55",
            "61","62","63","64","65","66","67","68","69",
            "71","73","74","75","77","79",
            "81","82","83","84","85","86","87","88","89",
            "91","92","93","94","95","96","97","98","99",
        ]
        ddd = digits[:2]
        if ddd not in valid_ddds:
            return ""

        return phone.strip()

    async def _enrich_from_page(self, client: httpx.AsyncClient, url: str) -> dict:
        result = {"phone": "", "email": "", "instagram": ""}
        if not url or not url.startswith("http"):
            return result

        try:
            resp = await client.get(url, timeout=15)
            if resp.status_code != 200:
                return result

            text = resp.text
            result["phone"] = self.extract_phone(text)
            result["email"] = self.extract_email(text)
            result["instagram"] = self.extract_instagram(text)
        except Exception:
            pass

        return result

    def _extract_domain(self, url: str) -> str:
        try:
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path
            domain = re.sub(r'^www\d?\.', '', domain)
            domain = domain.split("/")[0].split("?")[0]
            return domain.lower() if domain else ""
        except Exception:
            return ""
