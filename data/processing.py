import pandas as pd

def construir_dataframe(raw_data, version):
    if not raw_data:
        return None
    df = pd.DataFrame(raw_data)
    cols_drop = ['system:index', 'geo']
    df = df.drop(columns=[c for c in cols_drop if c in df.columns])
    df['year'] = df['year'].astype(int)
    df['version'] = version
    return df

def fusionar_versiones(dfs):
    return pd.concat(dfs, ignore_index=True) if dfs else None