import pandas as pd

def charger_fichier_sonde(file, skip_rows=10):
    """Charge un fichier de sonde avec métadonnées."""
    if file.name.endswith('.csv'):
        df = pd.read_csv(file, skiprows=skip_rows)
    else:
        df = pd.read_excel(file, skiprows=skip_rows)
    
    df = df.dropna(how="all").reset_index(drop=True)
    df.columns = [str(col).strip() for col in df.columns]
    
    # Fusion Date + Time si présent
    if len(df.columns) >= 2:
        df['Horodatage'] = pd.to_datetime(
            df.iloc[:, 0].astype(str) + ' ' + df.iloc[:, 1].astype(str),
            dayfirst=True,
            errors='coerce'
        )
    return df

def charger_fichier_classique(file):
    """Charge un fichier Excel/CSV standard."""
    if file.name.endswith('.csv'):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)
    return df.dropna(how="all").reset_index(drop=True)
