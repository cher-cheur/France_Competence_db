import pandas as pd
import requests
from io import BytesIO

def read_excel_from_url(url: str) -> pd.DataFrame:
    """
    Télécharge et lit un fichier Excel à partir d'une URL.

    Args:
        url (str): L'URL du fichier Excel.

    Returns:
        pd.DataFrame: Le contenu du fichier Excel sous forme de DataFrame.
    """
    response = requests.get(url)
    response.raise_for_status()  # Vérifie si la requête a réussi
    excel_data = BytesIO(response.content)
    return pd.read_excel(excel_data)
