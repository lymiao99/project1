import joblib, pandas as pd

scaler = joblib.load("models/scaler.pkl")
model = joblib.load("models/defect_severity_model.pkl")

df = pd.DataFrame([{
    "defect_type": "structural",
    "defect_location": "A1",
    "inspection_method": "visual",
    "product_id": "P063"
}])

X = scaler.transform(df)
print(X.shape)
print(model.predict(X))
print(model.predict_proba(X))
