import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_unstructured import UnstructuredLoader
from config import Config, logger
from charset_normalizer import from_path  # Для определения кодировки текстовых файлов


def create_vector_db():
    """
    Создаёт векторную базу данных из документов в папке `documents`.
    Поддерживает все форматы, которые может обработать UnstructuredLoader.
    """
    try:
        # Загрузка документов
        documents = []
        for root, _, files in os.walk("documents"):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    # Пропускаем определение кодировки для файлов .docx
                    if file.endswith(".docx"):
                        loader = UnstructuredLoader(file_path, mode="elements")
                    else:
                        # Определяем кодировку для текстовых файлов
                        result = from_path(file_path).best()
                        if result is None:
                            logger.warning(f"Не удалось определить кодировку файла {file}. Пропускаем.")
                            continue
                        encoding = result.encoding
                        logger.debug(f"Определена кодировка файла {file}: {encoding}")

                        # Используем новый загрузчик с указанием кодировки
                        loader = UnstructuredLoader(file_path, mode="elements", encoding=encoding)

                    # Загружаем документы
                    docs = loader.load()

                    # Добавляем метаданные с гиперссылкой
                    for doc in docs:
                        # Берём URL из словаря или используем путь к файлу, если URL нет
                        source_url = f"file://{os.path.abspath(file_path)}"
                        doc.metadata["source_url"] = source_url

                    documents.extend(docs)
                    logger.info(f"Файл {file} успешно загружен.")
                except Exception as e:
                    logger.error(f"Ошибка при загрузке файла {file_path}: {e}")

        # Проверка наличия документов
        if not documents:
            logger.warning("Нет документов для обработки.")
            return

        # Разделение текста на чанки
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        split_docs = text_splitter.split_documents(documents)

        # Проверка наличия чанков
        if not split_docs:
            logger.warning("После разделения текста нет чанков для обработки.")
            return

        # Создание эмбеддингов
        embeddings = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-large")

        # Создание векторной базы данных
        db = FAISS.from_documents(split_docs, embeddings)

        # Сохранение базы данных
        db.save_local("db/db_01")
        logger.info("Векторная база данных успешно создана!")

    except Exception as e:
        logger.error(f"Ошибка при создании векторной базы данных: {e}")


if __name__ == "__main__":
    create_vector_db()
