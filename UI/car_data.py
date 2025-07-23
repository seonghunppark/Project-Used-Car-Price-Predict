import pandas as pd

# 모델명 매핑
MODEL_MAP = {
    'grandeur': '그랜저',
    'grandeur_GN7': '그랜저 GN7',
    'grandeur_hybrid_GN7': '그랜저 GN7 하이브리드',
    'grandeur_IG': '그랜저 IG',
    'grandeur_IG_hybrid': '그랜저 IG 하이브리드',
    'grandeur_new_luxury': '그랜저 뉴 럭셔리',
    'grandeurHG': '그랜저 HG',
    'grandeurHG_hybrid': '그랜저 HG 하이브리드',
    'grandeurTG': '그랜저 TG',
    'new_grandeur': '뉴 그랜저',
    'the_luxury_grandeur': '더 럭셔리 그랜저',
    'the_new_grandeur_IG': '더 뉴 그랜저 IG',
    'the_new_grandeur_IG_hybrid': '더 뉴 그랜저 IG 하이브리드'
}

# 역매핑
REVERSE_MODEL_MAP = {v: f"model_{k}" for k, v in MODEL_MAP.items()}

def load_structured_car_data(csv_path):
    df = pd.read_csv(csv_path)

    # 오일 타입 복원
    oil_cols = [col for col in df.columns if col.startswith("oilingtype_")]
    oil_map = {
        'oilingtype_LPG': 'LPG',
        'oilingtype_diesel': '디젤',
        'oilingtype_gasoline': '가솔린',
        'oilingtype_hybrid': '하이브리드'
    }
    df['oilingtype'] = df[oil_cols].idxmax(axis=1).map(oil_map)

    # 모델명 복원
    model_cols = [col for col in df.columns if col.startswith("model_")]
    df['car_name'] = df[model_cols].idxmax(axis=1).str.replace("model_", "", regex=False).map(MODEL_MAP)

    # 연도 복원
    year_cols = [col for col in df.columns if col.startswith("year_")]
    df['year'] = df[year_cols].idxmax(axis=1).str.replace("year_", "", regex=False).astype(int)

    # 주행거리 복원
    mileage_cols = [col for col in df.columns if col.startswith("mileage_")]
    df['mileage'] = df[mileage_cols].idxmax(axis=1).str.replace("mileage_", "", regex=False).str.replace("_", " ~ ")

    return df[['car_name', 'year', 'oilingtype', 'mileage']]

def map_korean_name_to_column_name(korean_name: str) -> str:
    return REVERSE_MODEL_MAP.get(korean_name, "")

# 테스트
if __name__ == "__main__":
    df = load_structured_car_data("car_price_remove_one_hot_encoding.csv")
    print(df.columns.tolist())
    print(df.head())