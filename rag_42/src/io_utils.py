"""Entrada y salida de datos del proyecto: carga y guarda modelos como JSON.

Contiene dos funciones para cargar archivos JSON y validarlos con pydantic
(`load_dataset` y `load_search_results`) y otra para guardar cualquier modelo
pydantic como JSON (`save_model`). Es el único punto que lee y escribe estos
archivos, para que todos los comandos los carguen y los guarden igual.
"""
from pathlib import Path
from pydantic import BaseModel

from src.models import RagDataset, StudentSearchResults


def load_dataset(path: str | Path) -> RagDataset:
    """Lee un dataset desde JSON y lo valida como RagDataset.

    Args:
        path: Ruta del archivo JSON.

    Returns:
        El dataset validado.

    Raises:
        OSError: Si el archivo no existe o no se puede leer.
        ValueError: Si el JSON está mal formado o no encaja con el modelo.
    """
    json_path = Path(path)
    json_text = json_path.read_text(encoding="utf-8")
    return RagDataset.model_validate_json(json_text)


def save_model(model: BaseModel, path: str | Path) -> None:
    """Escribe `model` como JSON, creando el directorio destino si no existe.

    Args:
        model: Modelo pydantic a guardar.
        path: Ruta del archivo JSON de salida.

    Raises:
        OSError: Si no se puede crear la carpeta o escribir el archivo.
    """
    json_path = Path(path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_text = model.model_dump_json(indent=2)
    json_path.write_text(json_text, encoding="utf-8")


def load_search_results(path: str | Path) -> StudentSearchResults:
    """Lee unos resultados de búsqueda desde JSON y los valida.

    Args:
        path: Ruta del archivo JSON.

    Returns:
        Los resultados de búsqueda validados.

    Raises:
        OSError: Si el archivo no existe o no se puede leer.
        ValueError: Si el JSON está mal formado o no encaja con el modelo.
    """
    json_path = Path(path)
    json_text = json_path.read_text(encoding="utf-8")
    return StudentSearchResults.model_validate_json(json_text)
