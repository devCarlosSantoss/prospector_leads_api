import re
from difflib import SequenceMatcher
from typing import List
from urllib.parse import urlparse


class Deduplicator:
    def __init__(self, similarity_threshold: float = 0.85):
        self.threshold = similarity_threshold

    def deduplicate(self, leads: list[dict]) -> list[dict]:
        if not leads:
            return []

        unique = []
        seen_keys = set()

        for lead in leads:
            key = self._build_key(lead)
            if key and key in seen_keys:
                continue
            if key:
                seen_keys.add(key)

            # Fuzzy name matching against existing unique leads
            is_dup = False
            name = self._clean_name(lead.get("company_name", ""))
            phone = self._clean_phone(lead.get("phone", ""))
            site = self._clean_url(lead.get("website", ""))
            insta = self._clean_url(lead.get("instagram", ""))

            for existing in unique:
                if self._is_duplicate(name, phone, site, insta, existing):
                    is_dup = True
                    # Merge data - keep the richer version
                    self._merge_leads(existing, lead)
                    break

            if not is_dup:
                unique.append(lead)

        return unique

    def _build_key(self, lead: dict) -> str:
        phone = self._clean_phone(lead.get("phone", ""))
        site = self._clean_url(lead.get("website", ""))
        insta = self._clean_url(lead.get("instagram", ""))
        name = self._clean_name(lead.get("company_name", ""))

        parts = []
        if phone:
            parts.append(f"p:{phone}")
        if site:
            parts.append(f"s:{site}")
        if insta:
            parts.append(f"i:{insta}")
        if name:
            parts.append(f"n:{name[:20].lower()}")

        return "|".join(parts) if parts else None

    def _clean_name(self, name: str) -> str:
        if not name:
            return ""
        name = name.lower().strip()
        name = re.sub(r'[^\w\s]', '', name)
        name = re.sub(r'\s+', ' ', name)
        name = re.sub(r'\b(ltda|mei|eireli|sa|s/a|me|epp|limitada)\b', '', name)
        return name.strip()

    def _clean_phone(self, phone: str) -> str:
        if not phone:
            return ""
        digits = re.sub(r'\D', '', phone)
        # Remove country code if present for matching
        if len(digits) >= 12 and digits.startswith("55"):
            digits = digits[2:]
        # Normalize to 10-11 digits
        if len(digits) >= 10:
            return digits[-11:] if len(digits) >= 11 else digits[-10:]
        return digits

    def _clean_url(self, url: str) -> str:
        if not url:
            return ""
        url = url.lower().strip()
        url = re.sub(r'^https?://', '', url)
        url = re.sub(r'^www\.', '', url)
        url = url.rstrip('/')
        url = url.split('?')[0]
        return url

    def _is_duplicate(self, name: str, phone: str, site: str, insta: str, existing: dict) -> bool:
        # Exact phone match
        if phone and self._clean_phone(existing.get("phone", "")) == phone:
            return True

        # Exact site match
        if site and self._clean_url(existing.get("website", "")) == site:
            return True

        # Exact insta match
        if insta and self._clean_url(existing.get("instagram", "")) == insta:
            return True

        # Fuzzy name match (if we have names)
        if name and existing.get("company_name"):
            existing_name = self._clean_name(existing["company_name"])
            if existing_name:
                ratio = SequenceMatcher(None, name, existing_name).ratio()
                if ratio >= self.threshold:
                    return True

        return False

    def is_duplicate_against_db(self, lead: dict, db_leads: list) -> tuple[bool, object]:
        name = self._clean_name(lead.get("company_name", ""))
        phone = self._clean_phone(lead.get("phone", ""))
        site = self._clean_url(lead.get("website", ""))
        insta = self._clean_url(lead.get("instagram", ""))

        for existing in db_leads:
            existing_dict = {
                "company_name": existing.company_name or "",
                "phone": existing.phone or "",
                "website": existing.website or "",
                "instagram": existing.instagram or "",
            }
            if self._is_duplicate(name, phone, site, insta, existing_dict):
                return True, existing
        return False, None

    def _merge_leads(self, target: dict, source: dict):
        for key, value in source.items():
            if value and not target.get(key):
                target[key] = value
            elif key in ("phone", "website", "email", "instagram") and value:
                existing = target.get(key, "")
                if value and value != existing:
                    if isinstance(existing, str):
                        existing_values = [v.strip() for v in existing.split("|")]
                        if value not in existing_values:
                            target[key] = f"{existing} | {value}"
