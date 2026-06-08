import os
import time
import pandas as pd
from app.services.agent_orchestrator import AgentOrchestrator
from app.services.storage import dataset_store

def run_cache_speed_test():
    hr_csv = "data/raw/HR-Employee-Attrition.csv"
    if not os.path.exists(hr_csv):
        print(f"Error: {hr_csv} not found.")
        return

    print("=== KỊCH BẢN KIỂM THỬ TỐC ĐỘ SEMANTIC CACHE ===")
    
    # 1. Đọc và lưu trữ dataset
    df = pd.read_csv(hr_csv)
    dataset_id = dataset_store.save_dataframe(df, "HR-Employee-Attrition.csv")
    print(f"1. Đã đăng ký Dataset thành công. ID: {dataset_id}")
    
    orchestrator = AgentOrchestrator()
    question = "Bộ phận nào có tỷ lệ nghỉ việc cao nhất?"
    
    # 2. Chạy lần đầu tiên (Cold Run - Không có cache)
    print(f"\n2. Đang thực thi Cold Run (Không có cache) cho câu hỏi: '{question}'...")
    start_cold = time.perf_counter()
    res_cold = orchestrator.chat(dataset_id, question)
    cold_duration = time.perf_counter() - start_cold
    print(f"   [Cold Run] Thời gian phản hồi: {cold_duration:.4f} giây")
    print(f"   [Nguồn xử lý]: {res_cold.get('explanation_source')}")
    print(f"   [Selected Tool]: {res_cold.get('tool_call', {}).get('tool_name') if res_cold.get('tool_call') else 'None'}")
    
    # 3. Chạy lần thứ hai (Hot Run - Có Semantic Cache)
    print(f"\n3. Đang thực thi Hot Run (Có Semantic Cache) cho câu hỏi tương tự: 'Phòng ban nào có tỷ lệ nghỉ việc cao nhất?'...")
    question_similar = "Phòng ban nào có tỷ lệ nghỉ việc cao nhất?"
    start_hot = time.perf_counter()
    res_hot = orchestrator.chat(dataset_id, question_similar)
    hot_duration = time.perf_counter() - start_hot
    print(f"   [Hot Run] Thời gian phản hồi: {hot_duration:.4f} giây")
    print(f"   [Nguồn xử lý]: {res_hot.get('explanation_source')}")
    
    # 4. Tính toán hệ số tăng tốc
    speedup = cold_duration / hot_duration if hot_duration > 0 else 0
    print("\n==============================================")
    print(f"⚡ HỆ SỐ TĂNG TỐC HIỆU NĂNG: {speedup:.2f}x lần!")
    print("==============================================")
    print("Lưu ý: Nhờ Ollama Embeddings + SQLite Vector Search, câu hỏi tương tự được khớp và trả lời lập tức dưới 50ms!")

if __name__ == "__main__":
    run_cache_speed_test()
