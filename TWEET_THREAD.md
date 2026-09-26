## Post 1

LLMs can make dense data tables easier to use without giving a model database access. Ask “critical inverter jobs in Munster over €5k” and get a typed filter plan you can inspect.

## Post 2

The model returns JSON using an allow-list of fields and operators. The app validates the plan, repairs invalid output, then compiles parameterized SQLite filters. The model never writes or runs SQL.

## Post 3

I built a runnable mini demo with 2,500 synthetic work orders and 1,200 site inspections, SQLite, and local Ollama. It includes a sample DB and an integration check against Gemma and Qwen: [GitHub repo link]
