# =======================
# DeepSeek Cleaner Module
# =======================

import aiohttp
import sqlite3
import json
import os
import logging

from dotenv import load_dotenv  # Optional dependency
load_dotenv()  # Optional

logger = logging.getLogger(__name__)

class DeepSeekCleaner:
    def __init__(self, db_path="database/competitors.db", api_key=None):
        self.db_path = db_path
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY no configurada")

        # Crear tabla clean_promotions si no existe
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS clean_promotions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    competitor TEXT NOT NULL,
                    country TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    bonus_amount TEXT,
                    bonus_type TEXT,
                    conditions TEXT,
                    wagering TEXT,
                    valid_until TEXT,
                    url TEXT,
                    scraped_at TEXT NOT NULL,
                    hash_id TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    async def clean_latest_promotions(self, limit=100):
        # 1. Leer últimos registros de promotions
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM promotions ORDER BY scraped_at DESC LIMIT ?", (limit,)
            )
            promotions = [dict(row) for row in cursor.fetchall()]

        if not promotions:
            logger.warning("⚠️ No hay registros en promotions para limpiar")
            return 0

        # 2. Procesar con DeepSeek
        cleaned_promotions = []
        async with aiohttp.ClientSession() as session:
            for promo in promotions:
                prompt = f"""
                Eres un analista de marketing de casinos online.
                Recibiste esta promoción de la competencia:
                ---
                Título: {promo['title']}
                Descripción: {promo['description']}
                ---
                Tu tarea es:

                1. Filtrar relevancia: Devuelve resultados solo si la promoción está claramente relacionada con el sector de casinos online (ejemplo: bonus, free spins, promociones, torneos, jackpots, wagering).

                - Descarta promociones que no tengan relación con casinos.

                - Incluye el requisito de apuesta (“wagering requirement”) si está mencionado (por ejemplo: 35x, 50x bonus, etc.). Si no aparece, deja el campo vacío.

                - Descarta textos vagos o sin información suficiente sobre la oferta (ej. sin monto del bono, condiciones poco claras o inexistentes).

                2. Idioma de salida: Todas las respuestas deben estar en inglés.

                3. Formato de salida: Devuelve un JSON con la siguiente estructura:
                {{
                    "title": "string",
                    "description": "string",
                    "bonus_amount": "string",
                    "bonus_type": "Welcome Bonus | Deposit Bonus | Free Spins | Cashback | Tournament | Jackpot | Other",
                    "conditions": "string",
                    "wagering": "string",
                    "valid_until": "string"
                }}
                4. Condición de salida: Si la promoción no es relevante, responde únicamente con null.
                """

                data = {
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 400,
                    "temperature": 0.2
                }

                try:
                    async with session.post(
                        "https://api.deepseek.com/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json"
                        },
                        json=data
                    ) as resp:
                        result = await resp.json()
                        content = result["choices"][0]["message"]["content"].strip()

                        try:
                            parsed = json.loads(content)
                            if parsed:  # solo si no es null
                                promo.update(parsed)
                                cleaned_promotions.append(promo)
                        except Exception:
                            logger.warning(f"Respuesta no válida de DeepSeek: {content}")
                            continue
                except Exception as e:
                    logger.error(f"Error llamando a DeepSeek: {e}")
                    continue

        # 3. Guardar en clean_promotions
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for cp in cleaned_promotions:
                cursor.execute("""
                    INSERT OR REPLACE INTO clean_promotions (
                        competitor, country, title, description, bonus_amount,
                        bonus_type, conditions, wagering, valid_until, url, scraped_at, hash_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    cp["competitor"], cp["country"], cp["title"], cp["description"],
                    cp["bonus_amount"], cp["bonus_type"], cp["conditions"], cp.get("wagering", ""),
                    cp["valid_until"], cp["url"], cp["scraped_at"], cp["hash_id"]
                ))
            conn.commit()

        logger.info(f"✅ Limpieza completada: {len(cleaned_promotions)} registros válidos")
        return len(cleaned_promotions)
