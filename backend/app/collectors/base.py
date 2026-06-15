from abc import ABC, abstractmethod
from typing import Optional
import asyncio
import random
from app.config import SCRAPING_CONFIG

class BaseCollector(ABC):
    def __init__(self):
        self.name = self.__class__.__name__
        self.results = []
        self.errors = []

    @abstractmethod
    async def collect(self, niche: str, city: str, max_results: int = 30, country: str = "") -> list[dict]:
        pass

    def normalize_phone(self, phone: str) -> str:
        import re
        digits = re.sub(r'\D', '', phone)
        return digits

    def extract_phone(self, text: str) -> str:
        import re
        patterns = [
            r'(?:\+?55)?\s*\(?\d{2}\)?\s*\d{4,5}-?\d{4}',
            r'\d{4,5}-\d{4}',
        ]
        for p in patterns:
            match = re.search(p, text)
            if match:
                return self.normalize_phone(match.group())
        return ""

    def extract_email(self, text: str) -> str:
        import re
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        match = re.search(pattern, text)
        return match.group() if match else ""

    def extract_instagram(self, text: str) -> str:
        import re
        patterns = [
            r'(?:instagram\.com/|@)([a-zA-Z0-9_.]+)',
            r'insta\s*[:\s]*@?([a-zA-Z0-9_.]+)',
        ]
        for p in patterns:
            match = re.search(p, text, re.IGNORECASE)
            if match:
                handle = match.group(1)
                if len(handle) > 2 and len(handle) < 50:
                    return f"https://instagram.com/{handle}"
        return ""

    async def delay(self):
        min_s, max_s = SCRAPING_CONFIG["delay_between_requests"]
        await asyncio.sleep(random.uniform(min_s, max_s))

    def build_result(self, **kwargs) -> dict:
        return {
            "company_name": kwargs.get("company_name", ""),
            "category": kwargs.get("category", ""),
            "description": kwargs.get("description", ""),
            "website": kwargs.get("website", ""),
            "phone": kwargs.get("phone", ""),
            "whatsapp_link": kwargs.get("whatsapp_link", ""),
            "email": kwargs.get("email", ""),
            "instagram": kwargs.get("instagram", ""),
            "facebook": kwargs.get("facebook", ""),
            "address": kwargs.get("address", ""),
            "neighborhood": kwargs.get("neighborhood", ""),
            "lead_city": kwargs.get("lead_city", ""),
            "state": kwargs.get("state", ""),
            "zipcode": kwargs.get("zipcode", ""),
            "source": kwargs.get("source", self.name),
            "source_url": kwargs.get("source_url", ""),
            "collected_at": kwargs.get("collected_at", ""),
        }
