import os
import sys
import pandas as pd
from app.services.agent_orchestrator import AgentOrchestrator
from app.services.storage import dataset_store

def run_test():
    hr_csv = "data/raw/HR-Employee-Attrition.csv"
    mkt_csv = "data/raw/Marketing+Data/marketing_data.csv"
    
    if not os.path.exists(hr_csv):
        print(f"Error: {hr_csv} does not exist.")
        return
    if not os.path.exists(mkt_csv):
        print(f"Error: {mkt_csv} does not exist.")
        return

    print("--- 1. Testing HR Dataset Attrition ---")
    df_hr = pd.read_csv(hr_csv)
    dataset_id_hr = dataset_store.save_dataframe(df_hr, "HR-Employee-Attrition.csv")
    print(f"Saved HR dataset to store with ID: {dataset_id_hr}")
    
    orchestrator = AgentOrchestrator()
    
    hr_questions = [
        "Bộ phận (Department) nào có tỷ lệ nghỉ việc (attrition rate) cao nhất?",
        "Làm thêm giờ (Overtime) có ảnh hưởng thế nào đến tỷ lệ nghỉ việc?"
    ]
    
    for q in hr_questions:
        print(f"\n[Question]: {q}")
        res = orchestrator.chat(dataset_id_hr, q)
        tool_name = res.get('tool_call', {}).get('tool_name') if res.get('tool_call') else 'None'
        print(f"[Selected Tool]: {tool_name}")
        print(f"[Explanation Source]: {res.get('explanation_source')}")
        print(f"[Explanation]:\n{res.get('answer')}")

    print("\n--- 2. Testing Marketing Dataset Conversion ---")
    df_mkt = pd.read_csv(mkt_csv)
    dataset_id_mkt = dataset_store.save_dataframe(df_mkt, "marketing_data.csv")
    print(f"Saved Marketing dataset to store with ID: {dataset_id_mkt}")
    
    mkt_questions = [
        "Kênh mua sắm (Purchase Channel) nào đem lại nhiều lượt mua hàng nhất?",
        "Response rate theo Income Band thay đổi ra sao?"
    ]
    
    for q in mkt_questions:
        print(f"\n[Question]: {q}")
        res = orchestrator.chat(dataset_id_mkt, q)
        tool_name = res.get('tool_call', {}).get('tool_name') if res.get('tool_call') else 'None'
        print(f"[Selected Tool]: {tool_name}")
        print(f"[Explanation Source]: {res.get('explanation_source')}")
        print(f"[Explanation]:\n{res.get('answer')}")

if __name__ == "__main__":
    run_test()
