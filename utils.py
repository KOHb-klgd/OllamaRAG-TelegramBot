import os
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from typing import Optional, Tuple
from config import Config, logger


def get_index_db() -> Optional[FAISS]:
    """Загружает векторную базу данных."""
    embeddings = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-large")
    db_file_name = "db/db_01"

    if os.path.exists(f"{db_file_name}/index.faiss"):
        return FAISS.load_local(db_file_name, embeddings, allow_dangerous_deserialization=True)
    logger.warning("Векторная база данных не найдена.")
    return None


async def generate_response(query: str, use_context: bool = False) -> Tuple[str, Optional[list]]:
    """Генерирует ответ на запрос пользователя и возвращает цитируемые чанки."""
    llm = ChatOllama(model=Config.OLLAMA_MODEL, temperature=0)

    if use_context:
        db = get_index_db()
        if db:
            docs = db.similarity_search(query, k=3)
            # Формируем цитируемые чанки
            chunks_info = []
            for doc in docs:
                source = doc.metadata.get("source", "Неизвестный источник")
                section = doc.metadata.get("section", "Неизвестный раздел")
                content = doc.page_content[:500]  # Ограничим длину текста для удобства
                chunks_info.append({"source": source, "section": section, "content": content})

            # Формируем контекст для LLM
            context_text = "\n".join(
                [f"📄 Источник: {chunk['source']}\n🔖 Раздел: {chunk['section']}\n📝 Параграф: {chunk['content']}\n"
                 for chunk in chunks_info]
            )

            prompt = (
                f"""Ты технический специалист. Твоя задача давать ответы на вопросы. 
                Вот контекст, который нужно использовать для ответа на вопрос: {context_text}\n\n
                Внимательно подумай над приведенным контекстом. 
                Теперь просмотри вопрос пользователя: {query}\n
                Дай ответ на этот вопрос, используя вышеуказанный контекст на русском языке.
                Ответ должен быть понятен маленькому ребёнку и лицам со слабоумием.
                Ты можешь задавать любые наводящие вопросы пользователю чтобы повысить качество ответа на вопрос. 
                Всегда давай полный и развёрнутый ответ на вопрос.
                Ответ:"""
            )

            try:
                response = await llm.agenerate([[HumanMessage(content=prompt)]])
                logger.info(f"Ответ сгенерирован для запроса: {query}")
                return response.generations[0][0].text, chunks_info
            except Exception as e:
                logger.error(f"Ошибка при генерации ответа: {e}")
                return f"⚠️ Ошибка при генерации ответа: {e}", None
        else:
            logger.warning("Векторная база данных не найдена.")
            return "⚠️ Векторная база данных не найдена.", None
    else:
        try:
            response = await llm.agenerate([[HumanMessage(content=query)]])
            logger.info(f"Ответ сгенерирован для запроса: {query}")
            return response.generations[0][0].text, None
        except Exception as e:
            logger.error(f"Ошибка при обработке запроса: {e}")
            return f"⚠️ Ошибка при обработке запроса: {e}", None
