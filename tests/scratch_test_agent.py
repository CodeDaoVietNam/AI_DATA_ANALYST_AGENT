import traceback
from app.services.agent_orchestrator import AgentOrchestrator

try:
    print("Sending question to Agent...")
    orchestrator = AgentOrchestrator()
    result = orchestrator.chat("0eeed256-efe1-428a-9ff4-ca92ec519de2", "Vẽ biểu đồ doanh thu theo category")
    print("SUCCESS RESULT:")
    import json
    # Print only first 300 chars of chart data if present to avoid overflow
    if result.get("chart"):
        chart_truncated = str(result["chart"])[:300] + "..."
        print(f"Answer: {result['answer']}, Chart: {chart_truncated}")
    else:
        print(result)
except Exception as e:
    print("FAILED WITH ERROR:")
    traceback.print_exc()
