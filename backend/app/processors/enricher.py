import asyncio
import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.config import SCRAPING_CONFIG


class LeadEnricher:
    def __init__(self):
        self.headers = {"User-Agent": SCRAPING_CONFIG["user_agent"]}
        self._sem = asyncio.Semaphore(5)

    async def enrich(self, lead: dict) -> dict:
        tasks = []

        if lead.get("website"):
            tasks.append(self._analyze_website(lead["website"]))

        if lead.get("instagram"):
            tasks.append(self._check_instagram(lead["instagram"]))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, dict):
                    lead.update(result)

        # Auto-detect fields
        lead["has_website"] = bool(lead.get("website"))
        lead["has_whatsapp"] = bool(lead.get("whatsapp_link") or lead.get("phone"))
        lead["has_landing_page"] = self._detect_landing_page(lead.get("auto_notes", ""))

        return lead

    async def _analyze_website(self, url: str) -> dict:
        result = {
            "has_landing_page": False,
            "has_whatsapp": False,
            "website_status": "unknown",
            "auto_notes": "",
        }

        if not url or not url.startswith("http"):
            url = f"https://{url}"

        try:
            async with httpx.AsyncClient(
                timeout=10,
                follow_redirects=True,
                headers=self.headers,
                verify=False,
            ) as client:
                resp = await client.get(url)

                if resp.status_code >= 400:
                    result["website_status"] = "offline"
                    result["auto_notes"] = "Site offline ou erro de acesso"
                    return result

                result["website_status"] = "online"
                content = resp.text.lower()
                soup = BeautifulSoup(content, "html.parser")

                notes = []

                # Check for landing page indicators
                landing_signals = [
                    "landing", "lp-", "landing-page", "pagebuilder",
                    "utm_source", "lead", "captura", "formulário",
                ]
                for signal in landing_signals:
                    if signal in content:
                        result["has_landing_page"] = True
                        notes.append("Landing page detectada")
                        break

                # Check for WhatsApp button/link
                whatsapp_patterns = [
                    r'wa\.me', r'whatsapp\.com/send', r'api\.whatsapp',
                    r'whatsapp-button', r'class="[^"]*whatsapp[^"]*"',
                    r'id="[^"]*whatsapp[^"]*"', r'whatsapp-icon',
                ]
                for pattern in whatsapp_patterns:
                    if re.search(pattern, content):
                        result["has_whatsapp"] = True
                        notes.append("WhatsApp no site detectado")
                        break

                # Check for contact form
                form_signals = [
                    '<form', 'type="email"', 'type="text"', 'contact.php',
                    'contact-form', 'form-contato', 'formulario',
                ]
                has_form = any(signal in content for signal in form_signals)
                if has_form:
                    notes.append("Formulário de contato presente")
                else:
                    notes.append("Sem formulário de contato")

                # Check for modern framework (React, Vue, etc.)
                modern_signals = [
                    "__nuxt", "__next", "react", "vue", "svelte",
                    "data-v-", "v-bind", ":class", "ng-",
                ]
                if any(signal in content for signal in modern_signals):
                    notes.append("Site moderno (framework detectado)")
                else:
                    notes.append("Site estático/tradicional")

                # Check for blog
                if re.search(r'/blog|/noticias|/artigos', content):
                    notes.append("Blog presente")

                # Page load time
                if len(content) < 5000:
                    notes.append("Site muito simples/conteúdo mínimo")

                result["auto_notes"] = "; ".join(notes)

        except Exception as e:
            result["website_status"] = "error"
            result["auto_notes"] = f"Erro ao acessar site: {str(e)[:100]}"

        return result

    async def _check_instagram(self, url: str) -> dict:
        result = {"instagram_active": False, "auto_notes_insta": ""}
        # Basic check - just mark as potentially active if URL is valid
        if url and ("instagram.com" in url or url.startswith("@")):
            result["instagram_active"] = True
        return result

    def _detect_landing_page(self, notes: str) -> bool:
        if not notes:
            return False
        return "landing" in notes.lower() or "lp" in notes.lower()
