# Memory Systems implementation

Thư mục này chứa bản triển khai hoàn chỉnh:

- `config.py`: cấu hình đường dẫn, compact memory và provider
- `model_provider.py`: adapter cho OpenAI, custom OpenAI-compatible, Gemini,
  Anthropic, Ollama và OpenRouter
- `memory_store.py`: token estimator, `User.md`, extraction có confidence
  threshold, conflict handling và compact memory
- `agent_baseline.py`: chỉ nhớ trong cùng thread
- `agent_advanced.py`: short-term + persistent profile + compact memory
- `benchmark.py`: Standard Benchmark và Long-Context Stress Benchmark
- `test_agents.py`: test persistence, compaction, cross-session recall, prompt
  cost, correction và chống lưu fact nhiễu

Chạy:

```bash
pytest -q
python src/benchmark.py
```

Không cần API key cho test và benchmark offline. Khi có credential, agent có thể
khởi tạo model thật theo `LLM_PROVIDER` và `LLM_MODEL`.
