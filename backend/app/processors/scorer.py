import re
from urllib.parse import urlparse

DIRECTORY_DOMAINS = {
    "paginaamarela", "páginasamarelas", "yellowpages", "cylex",
    "guiatelefone", "telelistas", "listabrasil", "apontador",
    "eguias", "guiamais", "tudobem", "todosnegocios",
    "boaempresa", "empresasdobrasil", "solutudo", "encontraempresa",
    "guiafacil", "officiodirectory", "hotfrog", "mercadolivre",
    "facebook", "instagram", "twitter", "linkedin",
}


class LeadScorer:
    def __init__(self):
        self.weights = {
            "has_real_website": 30,
            "has_whatsapp": 15,
            "has_instagram": 10,
            "has_email": 10,
            "local_business": 15,
            "no_website": 30,
            "weak_website": 20,
            "instagram_no_website": 20,
            "no_whatsapp": 5,
            "no_email": 5,
            "social_only": 15,
        }

    def score(self, lead: dict) -> dict:
        score = 0
        reasons = []
        suggested_service = []

        website = lead.get("website", "") or ""
        instagram = lead.get("instagram", "") or ""
        phone = lead.get("phone", "") or ""
        email = lead.get("email", "") or ""
        name = lead.get("company_name", "") or ""
        lead_city = lead.get("lead_city", "") or ""
        niche = lead.get("niche", "") or lead.get("category", "") or ""

        is_directory = self._is_directory_url(website)
        is_social_only = self._is_social_url(website) and not is_directory
        has_real_website = bool(website) and not is_directory and not is_social_only

        has_instagram = bool(instagram) or bool(lead.get("instagram_active"))
        has_whatsapp = bool(phone) or bool(lead.get("whatsapp_link")) or bool(lead.get("has_whatsapp"))
        has_email = bool(email)

        if has_real_website:
            score += self.weights["has_real_website"]
            reasons.append("Site institucional presente")
            if self._check_weak_website(website):
                score += self.weights["weak_website"]
                reasons.append("Site de plataforma gratuita — precisa modernizar")
                suggested_service.append("Modernização de site")
                suggested_service.append("Landing page profissional")
            else:
                suggested_service.append("Landing page para campanhas")
                suggested_service.append("Automação de atendimento")
        elif is_social_only:
            score += self.weights["social_only"]
            reasons.append("Presença apenas em rede social")
            suggested_service.append("Site institucional")
            suggested_service.append("Landing page profissional")
        else:
            score += self.weights["no_website"]
            reasons.append("Sem site institucional")
            if has_instagram:
                score += self.weights["instagram_no_website"]
                reasons.append("Tem Instagram mas não tem site próprio")
                suggested_service.append("Site institucional")
                suggested_service.append("Landing page")
            else:
                suggested_service.append("Site institucional completo")
                suggested_service.append("Landing page")

        if has_whatsapp:
            score += self.weights["has_whatsapp"]
            reasons.append("WhatsApp disponível para contato")
        else:
            score += self.weights["no_whatsapp"]
            reasons.append("Sem WhatsApp comercial encontrado")

        if has_email:
            score += self.weights["has_email"]
            reasons.append("Email de contato encontrado")
        else:
            score += self.weights["no_email"]
            reasons.append("Email não encontrado publicamente")

        if has_instagram:
            score += self.weights["has_instagram"]
            reasons.append("Instagram ativo identificado")

        if lead_city or lead.get("address"):
            score += self.weights["local_business"]
            reasons.append("Negócio local — alta probabilidade de conversão")
            suggested_service.append("Landing page local")
            suggested_service.append("Google Meu Negócio")

        category = (lead.get("category") or lead.get("niche") or "").lower()
        high_intent_keywords = [
            "odontologia", "clínica", "consultório", "advocacia", "escritório",
            "salão", "barbearia", "academia", "restaurante", "pizzaria",
            "hotel", "pousada", "imobiliária", "corretor", "autônomo",
            "fisioterapia", "psicologia", "nutrição", "personal",
            "mecânica", "oficina", "construção", "arquitetura",
            "estética", "beleza", "cabelo", "sobrancelha", "design",
            "dog", "pet", "veterinário", "acupuntura",
            "massagem", "pilates", "yoga", "funcional",
        ]
        if any(kw in category for kw in high_intent_keywords):
            score += 10
            reasons.append(f"Nicho '{category}' com potencial de conversão")

        quality = self._get_quality(score)
        opportunity = self._get_opportunity(has_real_website, has_instagram, has_whatsapp, website, is_social_only)
        suggested_service = list(dict.fromkeys(suggested_service))

        return {
            "score": min(score, 100),
            "quality": quality,
            "score_reason": "; ".join(reasons),
            "opportunity": opportunity,
            "suggested_service": "; ".join(suggested_service) if suggested_service else "Análise comercial necessária",
            "suggested_message": self._generate_message(lead),
            "next_action": self._get_next_action(score, has_real_website, has_whatsapp, has_instagram, name),
        }

    def _is_directory_url(self, url: str) -> bool:
        if not url:
            return False
        try:
            domain = urlparse(url).netloc.lower()
            domain = re.sub(r'^www\d?\.', '', domain)
            base = domain.split('.')[0] if domain else ""
            return base in DIRECTORY_DOMAINS
        except Exception:
            return False

    def _is_social_url(self, url: str) -> bool:
        if not url:
            return False
        social = ["facebook.com", "instagram.com", "twitter.com", "linkedin.com"]
        try:
            domain = urlparse(url).netloc.lower()
            return any(s in domain for s in social)
        except Exception:
            return False

    def _check_weak_website(self, url: str) -> bool:
        if not url:
            return False
        weak_signals = [
            "wix.com", "wordpress.com", "blogspot.com", "webnode.com",
            "googlesites", "site123.com", "criandosite.com.br", "canva.com",
            "carrd.co", "templatemonster",
        ]
        url_lower = url.lower()
        for signal in weak_signals:
            if signal in url_lower:
                return True
        return False

    def _get_quality(self, score: int) -> str:
        if score >= 70:
            return "quente"
        elif score >= 40:
            return "morno"
        else:
            return "frio"

    def _get_opportunity(self, has_site: bool, has_insta: bool, has_whats: bool, website: str, social_only: bool) -> str:
        if not has_site and has_insta:
            return "Empresa com Instagram ativo mas sem site próprio"
        if not has_site and not has_insta:
            return "Empresa sem presença digital identificada"
        if social_only:
            return "Empresa presente apenas em redes sociais"
        if has_site and self._is_directory_url(website):
            return "Empresa listada em diretório mas sem site próprio"
        if has_site and not has_whats:
            return "Site existente mas sem canal de WhatsApp para atendimento"
        if has_site:
            return "Presença web existente — oportunidades de modernização e automação"
        return "Oportunidade de prospecção comercial"

    def _generate_message(self, lead: dict) -> str:
        name = lead.get("company_name", "") or ""
        if not name:
            return ""

        niche = (lead.get("niche") or lead.get("category") or "").strip()
        city = (lead.get("lead_city") or lead.get("city") or "").strip()
        website = (lead.get("website") or "").strip()
        has_site = bool(website)
        has_whats = bool(lead.get("phone") or lead.get("whatsapp_link") or lead.get("has_whatsapp"))
        has_insta = bool(lead.get("instagram") or lead.get("instagram_active"))
        has_landing = bool(lead.get("has_landing_page"))
        is_social = self._is_social_url(website)
        is_weak = self._check_weak_website(website)
        is_dir = self._is_directory_url(website)
        has_real_site = has_site and not is_dir and not is_social

        greetings = ["Olá", "Opa", "Fala", "Ei"]
        greeting = greetings[hash(name) % len(greetings)]

        if not has_site and has_insta:
            return (
                f"{greeting} {name}! 👋\n\n"
                f"Vi que vocês estão presentes no Instagram, mas reparei que ainda não têm um site próprio. "
                f"Um site institucional passa mais credibilidade e ajuda a converter seguidores em clientes de verdade. "
                f"Posso ajudar a criar um site profissional e integrado com o Instagram de vocês. "
                f"Vamos conversar sobre isso? 😊"
            )

        if not has_site and not has_insta:
            return (
                f"{greeting} {name}! 👋\n\n"
                f"Recentemente pesquisei sobre {niche or 'o ramo de vocês'} em {city or 'a região'} "
                f"e notei que {name} ainda não tem presença digital (site ou redes sociais). "
                f"Hoje em dia, ter um site é essencial para ser encontrado por novos clientes. "
                f"Gostaria de apresentar uma solução completa de site institucional + ferramentas digitais para o negócio de vocês. "
                f"Topa uma conversa rápida?"
            )

        if not has_real_site and has_insta:
            return (
                f"{greeting} {name}! 👋\n\n"
                f"Vi que vocês estão ativos nas redes sociais, mas senti falta de um site próprio. "
                f"Ter um site institucional ajuda a fortalecer a marca e passar mais confiança para quem pesquisa por {niche or 'seus serviços'} no Google. "
                f"Posso preparar uma proposta de site profissional para {name}. Me chama pra gente conversar? 😊"
            )

        if has_real_site and is_weak:
            return (
                f"{greeting} {name}! 👋\n\n"
                f"Acessei o site de vocês e vi que ele pode ser mais moderno e rápido. "
                f"Um site atualizado passa mais confiança e aparece melhor no Google. "
                f"Posso ajudar a criar um site profissional, otimizado para celular e com WhatsApp integrado. "
                f"Vamos conversar sobre isso?"
            )

        if has_real_site and not has_whats:
            return (
                f"{greeting} {name}! 👋\n\n"
                f"Vi que {name} tem site, mas não encontrei um canal de WhatsApp para atendimento rápido. "
                f"Sabia que colocar WhatsApp no site pode aumentar as conversas de clientes em até 40%? "
                f"Posso ajudar a integrar WhatsApp Business no site de vocês, além de outras melhorias. "
                f"Bora bater um papo?"
            )

        if has_real_site and has_whats and not has_landing:
            return (
                f"{greeting} {name}! 👋\n\n"
                f"{name} já tem site e WhatsApp, mas e as landing pages? "
                f"Landing pages são páginas focadas em campanhas específicas que convertem muito mais visitantes em clientes. "
                f"Posso apresentar como isso pode trazer ainda mais resultados para o negócio de vocês. "
                f"Vamos marcar uma conversa?"
            )

        return (
            f"{greeting} {name}! 👋\n\n"
            f"{name} já tem uma boa presença digital! 🚀\n\n"
            f"Gostaria de apresentar soluções para turbinar ainda mais os resultados: "
            f"automação de atendimento, CRM, campanhas pagas e estratégias avançadas. "
            f"Vou preparar uma proposta personalizada — podemos agendar uma call?"
        )

    def _get_next_action(self, score: int, has_site: bool, has_whats: bool, has_insta: bool, name: str) -> str:
        if score >= 70:
            if not has_site and has_insta:
                return f"Enviar mensagem para {name} no Instagram apresentando proposta de site institucional + landing page"
            if not has_site:
                return f"Pesquisar contato de {name} e oferecer criação de site profissional"
            if has_site and not has_whats:
                return f"Propor para {name} WhatsApp comercial + automação de atendimento"
            return f"Agendar reunião com {name} para apresentar soluções digitais"
        elif score >= 40:
            return f"Pesquisar mais sobre {name} e preparar proposta personalizada"
        elif score >= 20:
            return f"Coletar mais informações de {name} antes do primeiro contato"
        else:
            return f"Adicionar {name} à lista de prospecção para avaliação futura"
